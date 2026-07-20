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


def geocode_nominatim(address: str) -> Optional[Dict[str, float]]:
    try:
        r = req_lib.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "GeocodeWebApp/1.2"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
    except Exception:
        pass
    return None

def geocode_amap(address: str, key: str) -> Optional[Dict[str, float]]:
    try:
        r = req_lib.get(
            "https://restapi.amap.com/v3/geocode/geo",
            params={"address": address, "key": key, "output": "json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "1" and data.get("geocodes"):
            lng, lat = data["geocodes"][0]["location"].split(",")
            return {"lat": float(lat), "lng": float(lng)}
    except Exception:
        pass
    return None

def geocode_institution_nominatim(org: str, country: str) -> Optional[Dict[str, float]]:
    """用机构名+国家在 Nominatim 上查询机构级精确坐标（经纬度）。"""
    try:
        query = f"{org}, {country}" if country else org
        r = req_lib.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "GeocodeWebApp/1.2"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            time_module.sleep(1.0)
            return {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
    except Exception:
        pass
    return None

def _batch_nominatim_geocode(
    items: List[Tuple[str, str]],
    max_workers: int = 3,
) -> Dict[Tuple[str, str], Optional[Dict[str, float]]]:
    """批量查询 Nominatim，items = [(org, country), ...]

    遵守 Nominatim 速率限制（1次/秒），使用多线程并发但通过 sleep 控制速率。
    返回 {(org, country): {"lat": float, "lng": float}} 或 None（查询失败）。
    """
    if not items:
        return {}

    results: Dict[Tuple[str, str], Optional[Dict[str, float]]] = {}

    def _query_one(item: Tuple[str, str]) -> Tuple[Tuple[str, str], Optional[Dict[str, float]]]:
        org, country = item
        key = (org, country)
        try:
            query = f"{org}, {country}" if country else org
            r = req_lib.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1},
                headers={"User-Agent": "GeocodeWebApp/1.3"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            if data:
                results[key] = {"lat": float(data[0]["lat"]), "lng": float(data[0]["lon"])}
            else:
                results[key] = None
        except Exception:
            results[key] = None
        time_module.sleep(1.0)
        return key, results.get(key)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_query_one, item) for item in items]
        for future in as_completed(futures):
            future.result()

    return results

def _coord_missing(lat: Any, lng: Any) -> bool:
    """判断经纬度是否缺失（NaN / None / 0,0 占位）。"""
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        return True
    if lat_f != lat_f or lng_f != lng_f:  # NaN
        return True
    return abs(lat_f) < 1e-9 and abs(lng_f) < 1e-9

def _geocode_query(query: str, amap_key: str, use_nominatim: bool,
                   cache: Dict[str, Optional[Dict[str, float]]]) -> Optional[Dict[str, float]]:
    """带本地缓存的确定性地理编码：AMap（若配置 key）优先，Nominatim 兜底。"""
    if query in cache:
        return cache[query]
    coords = None
    if amap_key:
        coords = geocode_amap(query, amap_key)
        if coords:
            coords = {**coords, "provider": "amap"}
    if coords is None and use_nominatim:
        coords = geocode_nominatim(query)
        time_module.sleep(0.5)  # Nominatim 限速要求
        if coords:
            coords = {**coords, "provider": "nominatim"}
    cache[query] = coords
    return coords

def _geocode_affiliation_session(sess: Dict, amap_key: str, use_nominatim: bool) -> Dict:
    """对 affiliation 会话中坐标缺失的条目做确定性地理编码兜底，并回填结果。"""
    name_col_map = {
        "affiliation_country": "Country/Region",
        "affiliation_org":     "Organization",
        "affiliation_city":    "City1",
    }
    cache: Dict[str, Optional[Dict[str, float]]] = {}
    items = []
    filled = 0
    checked = 0

    for subtype in set(sess.get("affiliation_subtypes", [])):
        df = sess.get(f"parsed_df_{subtype}")
        name_col = name_col_map[subtype]
        if df is None or df.empty:
            # 尚未执行 AI 解析：直接从原始上传表初始化该子类型的结果表
            raw = sess.get("df")
            if raw is None or "_affiliation_type" not in raw.columns:
                continue
            df = raw[raw["_affiliation_type"] == subtype].copy()
            df = df.drop(columns=["_affiliation_type"], errors="ignore").reset_index(drop=True)
        if df.empty or name_col not in df.columns:
            continue
        for idx, row in df.iterrows():
            if not _coord_missing(row.get("lat"), row.get("lng")):
                continue
            name = str(row.get(name_col, "")).strip()
            if not name:
                continue
            checked += 1
            coords = _geocode_query(name, amap_key, use_nominatim, cache)
            if not coords:
                continue
            provider = coords.get("provider", "nominatim")
            df.at[idx, "lat"] = coords["lat"]
            df.at[idx, "lng"] = coords["lng"]
            df.at[idx, "ParseSrc"] = "geocode"
            df.at[idx, "ParseModel"] = provider
            filled += 1
            # 仅更新当前会话；不写入固定参考库
            items.append({
                "query": name, "subtype": subtype,
                "lat": coords["lat"], "lng": coords["lng"],
            })
        sess[f"parsed_df_{subtype}"] = df

    return {"total": len(items), "checked": checked, "filled": filled,
            "items": items, "field": "affiliation"}

