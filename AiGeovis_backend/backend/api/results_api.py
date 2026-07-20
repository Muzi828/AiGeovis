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

from core.sessions import sessions, parse_progress, stop_flags
from core.schemas import (
    AIConfig, ParseC1Request, GeocodeRequest, ListModelsRequest,
    ParseTierRequest, ParseBatchTiersRequest, StatsRequest,
    BenchmarkRequest, DuplicateRemoveRequest, ParseAffiliationRequest,
)
from core.i18n import ZH, _is_en, _tr, _tier_label, _tr_issues, _join_issues
from core.utils import df_page, parse_ai_json
from core.reexport import pull
import geo.country as _geo_country
import geo.address as _geo_address
import geo.prompts as _geo_prompts
import geo.ai_client as _geo_ai_client
import geo.geocoders as _geo_geocoders
import geo.reference_cache as _geo_reference_cache
import geo.parse_jobs as _geo_parse_jobs
import data.loaders as _data_loaders
import data.quality as _data_quality
import services.matrix as _svc_matrix
import services.viz as _svc_viz
import services.gml as _svc_gml

pull(_geo_country, globals())
pull(_geo_address, globals())
pull(_geo_prompts, globals())
pull(_geo_ai_client, globals())
pull(_geo_geocoders, globals())
pull(_geo_reference_cache, globals())
pull(_geo_parse_jobs, globals())
pull(_data_loaders, globals())
pull(_data_quality, globals())
pull(_svc_matrix, globals())
pull(_svc_viz, globals())
pull(_svc_gml, globals())


router = APIRouter()


@router.get("/api/geo/results")
def get_geo_results(session_id: str, page: int = 1, page_size: int = 50, field: str = "C1"):
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    file_type = sess.get("file_type", "wos")

    # ── affiliation 类型：返回 parsed_df_affiliation 的结果列表 ──
    if file_type == "affiliation":
        return _results_affiliation(sess, page, page_size, field=field)

    # ── WoS/BP 类型：走原有逻辑 ──
    df = _get_field_df(sess, field)
    cols = _field_cols(field)

    # 先按分号展开地址，确保每行只有一个地址
    df = _explode_address_field(df, field)
    wanted = [cols["country"], cols["org"], cols["city1"], cols["city2"], cols["lat"], cols["lng"]]
    # 保留原始字段列（如 C3）作为「Raw C3」展示，并据此按地址去重；
    # 否则前端 Raw C3 列全空，且 Total 会按展开后的地址行数（未去重）虚高。
    if field not in wanted:
        wanted.append(field)
    present = [c for c in wanted if c in df.columns]
    sub = df[present].copy()
    if field in sub.columns:
        sub[field] = sub[field].astype(str).str.strip()
        sub = sub[sub[field].ne("")]
        sub = sub.drop_duplicates(subset=[field], keep="first")

    # 统一重命名给前端，方便复用同一张表格
    # 注意：C3 场景下原始字段名 "C3" 不在 rename map 中，需单独保留
    rename = {
        cols["country"]: "Country/Region",
        cols["org"]:     "Organization",
        cols["city1"]:   "City1",
        cols["city2"]:   "City2",
        cols["lat"]:     "Latitude",
        cols["lng"]:     "Longitude",
        cols["src"]:     "ParseSrc",
        cols["model"]:   "ParseModel",
    }
    if field in sub.columns:
        rename[field] = "address"
    sub = sub.rename(columns=rename)

    def _row_needs_completion(row: pd.Series) -> bool:
        parsed = {
            "Country/Region": row.get("Country/Region", ""),
            "Organization": row.get("Organization", ""),
            "City1": row.get("City1", ""),
            "City2": row.get("City2", ""),
            "lat": row.get("Latitude", None),
            "lng": row.get("Longitude", None),
        }
        if field == "C3":
            return bool(_c3_result_issues(parsed))
        return bool(_parse_result_issues(parsed))

    # 排序：完整结果排前面，空字段/0经纬度排后面，方便用户查看和处理
    if not sub.empty:
        sub["_needs_completion"] = sub.apply(_row_needs_completion, axis=1)
        sub = sub.sort_values("_needs_completion", ascending=True).drop(columns=["_needs_completion"])
        sub = sub.reset_index(drop=True)

    # 统计待补全数量：包含空字段和 0/0 经纬度
    empty_count = int(sub.apply(_row_needs_completion, axis=1).sum()) if not sub.empty else 0

    result = df_page(sub, page, page_size)
    result["empty_count"] = empty_count
    return result

@router.get("/api/geo/viz-data")
def get_viz_data(session_id: str, field: str = "C1", top_n: int = 30):
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    file_type = sess.get("file_type", "wos")

    # ── affiliation 类型：直接返回 parsed_df_affiliation 的聚合结果 ──
    if file_type == "affiliation":
        subtype = field if field.startswith("affiliation") else (sess.get("affiliation_subtypes", ["affiliation_org"])[0] if sess.get("affiliation_subtypes") else "affiliation_org")
        return _viz_data_affiliation(sess, top_n, field=subtype)

    # ── WoS/BP 类型：走原有逻辑 ──
    df   = _get_field_df(sess, field)
    cols = _field_cols(field)

    # ── 解析进度统计 ──────────────────────────────
    if field in df.columns:
        all_vals  = df[field].dropna().astype(str).str.strip()
        total_uniq = int(all_vals[all_vals != ""].nunique())
    else:
        total_uniq = 0

    if cols["country"] in df.columns and field in df.columns:
        mask = (
            df[cols["country"]].astype(str).str.strip().ne("") &
            df[field].astype(str).str.strip().ne("")
        )
        parsed_uniq = int(df[mask][field].nunique())
    else:
        parsed_uniq = 0

    parse_stats = {
        "total":    total_uniq,
        "parsed":   parsed_uniq,
        "percent":  round(parsed_uniq / total_uniq * 100) if total_uniq else 0,
        "complete": total_uniq > 0 and parsed_uniq >= total_uniq,
    }
    has_any = parsed_uniq > 0

    if not has_any:
        return {
            "field": field, "parsed": False,
            "parse_stats":    parse_stats,
            "country_counts": [], "org_counts": [], "city_counts": [],
            "geocode_items":  [],
        }

    # ── 整体计数（whole counting）：按【文献 × 实体】去重，一篇论文里同一国家/城市/机构
    #    只计一次，与分层统计（get_tier_stats）和共现矩阵口径一致，避免同一论文多地址重复放大。──
    working = _unified_addr_entities_by_paper(sess, field)
    if working.empty:
        return {
            "field": field, "parsed": True,
            "parse_stats":    parse_stats,
            "country_counts": [], "org_counts": [], "city_counts": [],
            "geocode_items":  [],
        }

    w = working.reset_index()
    w["_lat"] = pd.to_numeric(w["_lat"], errors="coerce")
    w["_lng"] = pd.to_numeric(w["_lng"], errors="coerce")

    def _tier_whole_counts(key: str, *, exclude_china_regions: bool = False):
        sub = w[w[key].astype(str).str.strip().ne("")]
        if sub.empty:
            return []
        if exclude_china_regions:
            sub = sub[~sub[key].map(is_china_region_entity)]
            if sub.empty:
                return []
        ded = sub.drop_duplicates(subset=["paper_idx", key])
        cnt = ded.groupby(key).size().sort_values(ascending=False).head(top_n)
        return [{"name": str(k), "value": int(v)} for k, v in cnt.items()]

    # 国家层：台/港/澳不单独计入；机构/城市层仍保留其规范标注
    country_counts = _tier_whole_counts("_country", exclude_china_regions=True)
    org_counts     = _tier_whole_counts("_org")
    city_counts    = _tier_whole_counts("_city")

    # ── 地图点：C3 以机构为最小粒度、C1 以国家为粒度；count 同样用整体计数（论文数）──
    point_key = "_org" if field == "C3" else "_country"
    geocode_items = []
    sub = w[w[point_key].astype(str).str.strip().ne("")]
    if field != "C3" and not sub.empty:
        sub = sub[~sub[point_key].map(is_china_region_entity)]
    if not sub.empty:
        ded = sub.drop_duplicates(subset=["paper_idx", point_key])
        counts = ded.groupby(point_key).size().sort_values(ascending=False).head(top_n)
        for kv, cnt in counts.items():
            g = sub[sub[point_key] == kv]
            coord = g[["_lat", "_lng"]].dropna()
            if coord.empty:
                continue
            lat_v = float(coord["_lat"].iloc[0]); lng_v = float(coord["_lng"].iloc[0])
            if not (-90 <= lat_v <= 90 and -180 <= lng_v <= 180):
                continue
            rep_country = g["_country"][g["_country"].astype(str).str.strip().ne("")]
            rep_city    = g["_city"][g["_city"].astype(str).str.strip().ne("")]
            geocode_items.append({
                "country":      (str(rep_country.mode().iloc[0]) if not rep_country.empty
                                 else (str(kv) if field != "C3" else "")),
                "organization": str(kv) if field == "C3" else "",
                "city":         (str(rep_city.mode().iloc[0]) if not rep_city.empty else ""),
                "lat":  round(lat_v, 5),
                "lng":  round(lng_v, 5),
                "count": int(cnt),
            })
    return {
        "field":          field,
        "parsed":         True,
        "parse_stats":    parse_stats,
        "country_counts": country_counts,
        "org_counts":     org_counts,
        "city_counts":    city_counts,
        "geocode_items":  geocode_items,
    }

@router.get("/api/geo/stats")
def get_tier_stats(session_id: str, field: str = "C1", tier: str = "country", top_n: int = 30):
    """
    Tiered statistics: aggregate by country / city / organization independently,
    each with its own coordinates and publication counts.
    - tier=country: aggregate by Country, using Country_Lat/Country_Lng
    - tier=city:    aggregate by (Country, City), using City_Lat/City_Lng
    - tier=org:     aggregate by (Country, Org), using Org_Lat/Org_Lng
    """
    if tier not in ("country", "city", "org"):
        raise HTTPException(status_code=400, detail=ZH.S_7cdc1fa367)

    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    df_key = _tier_parsed_df_key(field, tier)
    if df_key not in sess:
        return {"tier": tier, "field": field, "parsed": False, "total": 0, "items": []}

    df = sess[df_key]
    cols = _tier_cols(field, tier)
    name_col = cols["name"]
    lat_col  = cols["lat"]
    lng_col  = cols["lng"]
    src_col  = cols["src"]

    if name_col not in df.columns:
        return {"tier": tier, "field": field, "parsed": False, "total": 0, "items": []}

    # ── 整体计数（whole counting）：按【文献 × 实体】去重，一篇论文里同一国家/机构只计一次，
    #    与共现矩阵口径一致，对齐 WoS「Countries/Regions」的记录数（避免同一论文多地址重复放大）。──
    country_col = _tier_cols(field, "country")["name"]
    working = _tier_address_entities_by_paper(sess, field, tier)
    if working.empty:
        return {"tier": tier, "field": field, "parsed": True, "total": 0, "items": []}

    _blank = ("", "nan", "none", "null")
    w = working.reset_index()
    w["_name"] = w[name_col].astype(str).str.strip()
    w = w[~w["_name"].str.lower().isin(_blank)].copy()
    if w.empty:
        return {"tier": tier, "field": field, "parsed": True, "total": 0, "items": []}

    # 国家层：中国台湾 / 香港 / 澳门不单独计入频次与地图
    if tier == "country":
        w = w[~w["_name"].map(is_china_region_entity)].copy()
        if w.empty:
            return {"tier": tier, "field": field, "parsed": True, "total": 0, "items": []}

    if country_col in w.columns:
        w["_country"] = w[country_col].astype(str).str.strip()
        w.loc[w["_country"].str.lower().isin(_blank), "_country"] = ""
    else:
        w["_country"] = ""

    # 实体唯一键：与 _make_entity_id 保持一致（country=规范化国家名；city/org=名称本身）
    w["_eid"] = [
        _make_entity_id(tier, nm, (ct or None))
        for nm, ct in zip(w["_name"], w["_country"])
    ]
    w = w[w["_eid"].astype(str).str.strip().ne("")]
    if w.empty:
        return {"tier": tier, "field": field, "parsed": True, "total": 0, "items": []}

    w["_lat"] = pd.to_numeric(w[lat_col], errors="coerce")
    w["_lng"] = pd.to_numeric(w[lng_col], errors="coerce")

    stats_rows = []
    for eid, g in w.groupby("_eid", sort=False):
        paper_count = int(g["paper_idx"].nunique())  # 整体计数 = 出现该实体的论文数
        if tier == "country":
            disp_name = eid
            disp_country = eid
        else:
            disp_name = str(g["_name"].iloc[0]).strip()
            nonempty = g["_country"][g["_country"].ne("")]
            disp_country = str(nonempty.mode().iloc[0]) if not nonempty.empty else ""
        coord = g[["_lat", "_lng"]].dropna()
        if not coord.empty:
            lat_v = float(coord["_lat"].iloc[0])
            lng_v = float(coord["_lng"].iloc[0])
        else:
            lat_v = lng_v = None
        stats_rows.append((disp_name, disp_country, paper_count, lat_v, lng_v))

    stats_rows.sort(key=lambda x: x[2], reverse=True)
    stats_rows = stats_rows[:top_n]

    items = []
    for disp_name, disp_country, paper_count, lat_v, lng_v in stats_rows:
        item = {
            "name":  disp_name,
            "count": paper_count,
            "lat":   round(lat_v, 5) if lat_v is not None else None,
            "lng":   round(lng_v, 5) if lng_v is not None else None,
        }
        if tier in ("city", "org"):
            item["country"] = disp_country
        items.append(item)

    total = int(sum(item["count"] for item in items))
    return {
        "tier":   tier,
        "field":  field,
        "parsed": True,
        "total":  total,
        "items":  items,
    }

@router.get("/api/geo/tier-results")
def get_tier_results(session_id: str, field: str = "C1", tier: str = "country",
                    page: int = 1, page_size: int = 50):
    """Get tiered parse results (paginated)."""
    if tier not in ("country", "city", "org"):
        raise HTTPException(status_code=400, detail=ZH.S_7cdc1fa367)

    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    df_key = _tier_parsed_df_key(field, tier)
    if df_key not in sess:
        return {"total": 0, "page": page, "page_size": page_size, "records": []}

    df = sess[df_key]
    cols = _tier_cols(field, tier)

    df = _explode_address_field(df, field)
    wanted = [field] + list(cols.values())
    present = [c for c in wanted if c in df.columns]
    sub = df[present].copy()
    if field in sub.columns:
        sub[field] = sub[field].astype(str).str.strip()
        sub = sub[sub[field].ne("")]
        sub = sub.drop_duplicates(subset=[field], keep="first")

    total = len(sub)
    start = (page - 1) * page_size
    end = start + page_size
    chunk = sub.iloc[start:end].copy()
    chunk = chunk.fillna("").astype(str)

    rename_map = {
        cols["name"]:  "name",
        cols["lat"]:   "lat",
        cols["lng"]:   "lng",
        cols["src"]:   "src",
        cols["model"]: "model",
        field:         "address",
    }
    chunk = chunk.rename(columns=rename_map)
    chunk["lat"] = chunk["lat"].apply(
        lambda x: round(float(x), 5) if x.strip() not in ("", "nan", "None") else None
    )
    chunk["lng"] = chunk["lng"].apply(
        lambda x: round(float(x), 5) if x.strip() not in ("", "nan", "None") else None
    )

    return {"total": total, "page": page, "page_size": page_size,
            "records": chunk.to_dict(orient="records")}

@router.get("/api/geo/tier-progress")
def get_tier_progress(session_id: str):
    """Query the parse progress of each tier."""
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    df = sess.get("df", pd.DataFrame())
    result = {}
    for field in ("C1", "C3"):
        if field not in df.columns:
            continue
        result[field] = {}
        for tier in ("country", "city", "org"):
            df_key = _tier_parsed_df_key(field, tier)
            if df_key in sess:
                tier_df = sess[df_key]
                cols = _tier_cols(field, tier)
                name_col = cols["name"]
                if name_col in tier_df.columns:
                    exploded = _explode_address_field(tier_df, field)
                    total_uniq = exploded[field].dropna().astype(str).str.strip()
                    total_uniq = total_uniq[total_uniq != ""]
                    total = int(total_uniq.nunique())
                    parsed_vals = (
                        exploded[exploded[name_col].astype(str).str.strip().ne("")][field]
                        .dropna().astype(str).str.strip()
                    )
                    parsed = int(parsed_vals[parsed_vals != ""].nunique())
                    result[field][tier] = {
                        "total": total,
                        "parsed": parsed,
                        "percent": round(parsed / total * 100) if total else 0,
                        "complete": total > 0 and parsed >= total,
                    }
                else:
                    result[field][tier] = {"total": 0, "parsed": 0, "percent": 0, "complete": False}
            else:
                result[field][tier] = {"total": 0, "parsed": 0, "percent": 0, "complete": False}
    return result

