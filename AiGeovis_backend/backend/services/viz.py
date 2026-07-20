from __future__ import annotations

import os
import sys
import json
import math
import re
import uuid
import time as time_module
import tempfile
import threading
import traceback
import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable

import pandas as pd
import numpy as np
import requests as req_lib

from fastapi import (
    APIRouter, FastAPI, UploadFile, File, HTTPException, BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.paths import BACKEND_DIR, PROJECT_ROOT

from core.reexport import pull
import geo.address as _geo_address
pull(_geo_address, globals())

from core.utils import df_page

def _results_affiliation(sess: Dict, page: int, page_size: int, field: str = "affiliation") -> Dict:
    """生成 affiliation 类型的解析结果列表（分页），返回与 C1 完全一致的结构。"""
    subtype = field if field.startswith("affiliation") else (sess.get("affiliation_subtypes", ["affiliation_org"])[0] if sess.get("affiliation_subtypes") else "affiliation_org")
    df = sess.get(f"parsed_df_{subtype}")
    if df is None or df.empty:
        return {"total": 0, "page": page, "page_size": page_size, "records": [], "empty_count": 0}

    df = df.copy()

    # 确定 name 列名（子类型决定 name → 哪个标准字段）
    if subtype == "affiliation_country":
        name_col = "Country/Region"
        out_name_col = "Country/Region"
    elif subtype == "affiliation_city":
        name_col = "City1"
        out_name_col = "City1"
    else:
        name_col = "Organization"
        out_name_col = "Organization"

    # 列重命名映射：df 列名 → 前端表格标准列名（与条形图/地图实体名一致）
    col_map = {
        name_col:     out_name_col,
        "lat":        "Latitude",
        "lng":        "Longitude",
        "count":      "count",
        "ParseSrc":   "ParseSrc",
        "ParseModel": "ParseModel",
    }
    wanted = [name_col, "lat", "lng", "count", "ParseSrc", "ParseModel"]
    present = [c for c in wanted if c in df.columns]
    sub = df[present].copy()
    sub = sub.rename(columns={k: v for k, v in col_map.items() if k in present})

    # 判断是否需要补全：仅检查经纬度
    def _row_needs_completion(row) -> bool:
        lat = row.get("Latitude")
        lng = row.get("Longitude")
        try:
            if lat is None or lng is None or (abs(float(lat)) < 1e-9 and abs(float(lng)) < 1e-9):
                return True
        except (TypeError, ValueError):
            return True
        return False

    # 排序：先按 count 倒序（多的在前），已解析的排前面
    if not sub.empty:
        has_count = "count" in sub.columns
        if has_count:
            sub["_sort_count"] = pd.to_numeric(sub["count"], errors="coerce").fillna(0)
        sub["_needs_completion"] = sub.apply(_row_needs_completion, axis=1)
        sort_keys = ["_needs_completion", "_sort_count"] if has_count else ["_needs_completion"]
        ascending = [True, False] if has_count else [True]
        drop_cols = ["_needs_completion", "_sort_count"] if has_count else ["_needs_completion"]
        sub = sub.sort_values(sort_keys, ascending=ascending).drop(columns=drop_cols)
        sub = sub.reset_index(drop=True)

    empty_count = int(sub.apply(_row_needs_completion, axis=1).sum()) if not sub.empty else 0

    total = len(sub)
    start = (page - 1) * page_size
    end = start + page_size

    if start >= total:
        return {"total": total, "page": page, "page_size": page_size,
                "records": [], "empty_count": empty_count}

    chunk = sub.iloc[start:end].copy().fillna("").astype(str).replace("", "")

    # 转换经纬度
    def _format_coord(val):
        try:
            if val in ("", "nan", "None") or (isinstance(val, str) and val.lower() in ("nan", "none", "inf")):
                return None
            f = float(val)
            if f != f or abs(f) == float("inf"):  # NaN 或 Infinity
                return None
            return round(f, 5)
        except (TypeError, ValueError):
            return None

    if "Latitude" in chunk.columns:
        chunk["Latitude"] = chunk["Latitude"].apply(_format_coord)
    if "Longitude" in chunk.columns:
        chunk["Longitude"] = chunk["Longitude"].apply(_format_coord)

    # 转换 count 列（如果存在）
    if "count" in chunk.columns:
        chunk["count"] = chunk["count"].apply(
            lambda x: int(float(x)) if str(x).strip() not in ("", "nan", "None") else 0
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": chunk.to_dict(orient="records"),
        "empty_count": empty_count,
    }

def _viz_data_affiliation(sess: Dict, top_n: int = 30, field: str = "affiliation") -> Dict:
    """生成 affiliation 类型的可视化数据，返回与 C1 完全一致的结构。"""
    subtype = field if field.startswith("affiliation") else (sess.get("affiliation_subtypes", ["affiliation_org"])[0] if sess.get("affiliation_subtypes") else "affiliation_org")
    df = sess.get(f"parsed_df_{subtype}")
    if df is None or df.empty:
        return {
            "field":          subtype,
            "parsed":         False,
            "parse_stats":    {"total": 0, "parsed": 0, "percent": 0, "complete": False},
            "country_counts": [], "org_counts": [], "city_counts": [],
            "geocode_items":  [],
        }

    df = df.copy()

    # 根据子类型确定 name 列
    if subtype == "affiliation_country":
        name_col = "Country/Region"
    elif subtype == "affiliation_city":
        name_col = "City1"
    else:
        name_col = "Organization"

    # ── 解析进度统计 ──
    total = int(len(df))
    parsed_count = int(
        (
            df["lat"].notna() & df["lng"].notna() &
            ((df["lat"].abs() > 1e-9) | (df["lng"].abs() > 1e-9))
        ).sum()
    )
    parse_stats = {
        "total":    total,
        "parsed":   parsed_count,
        "percent":  round(parsed_count / total * 100) if total else 0,
        "complete": parsed_count >= total,
    }

    if parsed_count == 0:
        return {
            "field":          subtype,
            "parsed":         True,
            "parse_stats":    parse_stats,
            "country_counts": [], "org_counts": [], "city_counts": [],
            "geocode_items":  [],
        }

    # ── 按子类型填充对应 counts（优先用 count 列，与地图/解析结果同步）──
    work = df[[name_col]].copy()
    work["_name"] = work[name_col].astype(str).str.strip()
    work = work[work["_name"].ne("") & ~work["_name"].str.lower().isin(("nan", "none"))]
    if subtype == "affiliation_country":
        from geo.country import is_china_region_entity
        work = work[~work["_name"].map(is_china_region_entity)]
    if "count" in df.columns:
        work["_count"] = pd.to_numeric(df.loc[work.index, "count"], errors="coerce").fillna(1).astype(int)
    else:
        work["_count"] = 1
    agg = (
        work.groupby("_name", as_index=False)["_count"]
        .sum()
        .sort_values("_count", ascending=False)
        .head(top_n)
    )
    counts_list = [{"name": str(r["_name"]), "value": int(r["_count"])} for _, r in agg.iterrows()]
    top_names = set(agg["_name"].astype(str).tolist())

    country_counts = counts_list if subtype == "affiliation_country" else []
    org_counts     = counts_list if subtype == "affiliation_org"     else []
    city_counts    = counts_list if subtype == "affiliation_city"   else []

    # ── 地图散点：与 counts 使用同一批 top_n 实体，保证各图数据一致 ──
    geocode_items = []
    if "lat" in df.columns and "lng" in df.columns and top_names:
        geo_df = df[[name_col, "lat", "lng", "count"]].copy()
        geo_df = geo_df.rename(columns={name_col: "_name"})
        geo_df["_name"] = geo_df["_name"].astype(str).str.strip()
        geo_df = geo_df[
            geo_df["_name"].isin(top_names) &
            geo_df["lat"].notna() &
            geo_df["lng"].notna()
        ]
        # 按 count 倒序排，多的点排前面
        if "count" in geo_df.columns:
            geo_df["_sort_count"] = pd.to_numeric(geo_df["count"], errors="coerce").fillna(0)
            geo_df = geo_df.sort_values("_sort_count", ascending=False).drop(columns=["_sort_count"])
            geo_df = geo_df.reset_index(drop=True)

        seen = set()
        for _, r in geo_df.iterrows():
            try:
                lat = float(r["lat"]); lng = float(r["lng"])
            except (TypeError, ValueError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue

            key = (str(r["_name"]).strip(), round(lat, 3), round(lng, 3))
            if key in seen:
                continue
            seen.add(key)

            count_val = int(r["count"]) if pd.notna(r["count"]) else 1
            item = {
                "country": "", "org": "", "organization": "", "city": "", "City1": "",
                "lat": round(lat, 5), "lng": round(lng, 5),
                "count": count_val,
            }
            name_text = str(r["_name"]).strip()
            if subtype == "affiliation_country":
                item["country"] = name_text
                item["name"] = name_text
            elif subtype == "affiliation_org":
                item["org"] = name_text
                item["organization"] = name_text
                item["name"] = name_text
            else:
                item["city"] = name_text
                item["City1"] = name_text
                item["name"] = name_text

            geocode_items.append(item)
            if len(geocode_items) >= top_n:
                break

    return {
        "field":          subtype,
        "parsed":         True,
        "parse_stats":    parse_stats,
        "country_counts": country_counts,
        "org_counts":     org_counts,
        "city_counts":    city_counts,
        "geocode_items":  geocode_items,
    }

