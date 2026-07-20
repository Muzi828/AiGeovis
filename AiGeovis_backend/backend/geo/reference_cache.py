from __future__ import annotations

from core.i18n import ZH

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

from core.paths import BACKEND_DIR
from geo.address import _to_float_or_none, rule_parse_c1
from geo.country import _normalize_country, _lookup_country_coords
from geo.address import _to_float_or_none
from geo.country import _lookup_country_coords, _normalize_country

def _affiliation_parse_json(text: str) -> Dict:
    """解析 AI 返回的经纬度 JSON"""
    defaults = {"lat": None, "lng": None}
    try:
        obj = json.loads(text.strip())
        defaults.update(obj)
    except json.JSONDecodeError:
        try:
            decoder = json.JSONDecoder(raw=True)
            obj, _ = decoder.raw_decode(text)
            defaults.update(obj)
        except (json.JSONDecodeError, ValueError):
            pass

    for k in ("lat", "lng"):
        v = defaults[k]
        try:
            defaults[k] = float(v) if v not in (None, "", "null") else None
        except (TypeError, ValueError):
            defaults[k] = None

    return defaults

_CACHE_DB = BACKEND_DIR / "affiliation_cache.db"

def _affiliation_cache_get(name: str) -> Optional[Dict]:
    """只读查询固定参考库；命中返回结果字典，否则返回 None。

    大小写不敏感匹配：库内 name 存的是「去空格 + 转小写」的规范 key，
    这里把用户解析出的名称同样归一化后再精确查主键（命中主键索引，快）。
    命中后仅取经纬度，显示仍沿用调用方（用户上传数据）的原始大小写。
    """
    import sqlite3
    if not _CACHE_DB.exists():
        return None
    if not name:
        return None
    key = name.strip().lower()
    if not key:
        return None
    try:
        # mode=ro：以只读方式打开，从连接层面禁止任何写盘操作
        uri = f"file:{_CACHE_DB.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=10)
        row = conn.execute(
            "SELECT lat, lng, src, model FROM affiliation_cache WHERE name = ?",
            (key,)
        ).fetchone()
        conn.close()
        if row is None:
            return None
        lat, lng, src, model = row
        result = {"lat": lat, "lng": lng, "_src": src or "db", "_model": model or "wos-ref"}
        issues = _affiliation_result_issues(result)
        return None if issues else result
    except Exception:
        return None

def _affiliation_result_issues(result: Dict) -> List[str]:
    """检查 affiliation 解析结果：仅验证经纬度"""
    issues = []
    lat = _to_float_or_none(result.get("lat"))
    lng = _to_float_or_none(result.get("lng"))
    if lat is None or lng is None:
        issues.append(ZH.S_1a2b0de102)  # 经纬度为空
    elif abs(lat) < 1e-9 and abs(lng) < 1e-9:
        issues.append(ZH.S_a20759f68f)  # 经纬度为0
    elif lat is not None and not (-90.0 < lat < 90.0):
        issues.append(ZH.S_12e6cd7bf4)  # 纬度越界
    elif lng is not None and not (-180.0 < lng < 180.0):
        issues.append(ZH.S_dd81478f85)  # 经度越界
    return issues

def _tier_ref_key(tier: str, c1: str) -> str:
    """从原始地址串中抽取用于参考库匹配的原始 token。

    参考库的 key 是 WoS 原始写法（如国家 "Peoples R China"、机构 "Chinese Acad Sci"），
    因此这里返回未归一化的原始片段：
      · country → 末段（去掉句点/作者前缀）
      · org     → 首段
    _affiliation_cache_get 内部会统一「去空格 + 转小写」后再匹配。
    """
    if not c1:
        return ""
    parts = c1.split("]", 1)
    addr = parts[1].strip() if len(parts) > 1 else c1
    segs = [s.strip() for s in addr.split(",") if s.strip()]
    if not segs:
        return ""
    if tier == "country":
        return segs[-1].rstrip(".").strip()
    if tier == "org":
        return segs[0].strip()
    return ""

_REF_COUNTRY_NORM_INDEX: Optional[Dict[str, Tuple[float, float, str]]] = None

def _ref_country_norm_index() -> Dict[str, Tuple[float, float, str]]:
    """构建【规范化国家名 → (lat, lng, model)】索引（源自参考库 country 行，只读 + 缓存）。

    WoS 全记录解析会把 C1 里的国家规范化（如 "Peoples R China" → "China"），
    而参考库国家 key 存的是 WoS 原文（"peoples r china"），二者直接精确匹配会漏掉。
    这里把库内 244 条国家行按 _normalize_country 后的名字重新建索引，坐标仍取自参考库，
    从而既能命中规范化后的国家名，又保证坐标与发布数据集完全一致。
    """
    global _REF_COUNTRY_NORM_INDEX
    if _REF_COUNTRY_NORM_INDEX is not None:
        return _REF_COUNTRY_NORM_INDEX
    idx: Dict[str, Tuple[float, float, str]] = {}
    import sqlite3
    try:
        if _CACHE_DB.exists():
            uri = f"file:{_CACHE_DB.resolve().as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10)
            for name, lat, lng, model in conn.execute(
                "SELECT name, lat, lng, model FROM affiliation_cache WHERE src = 'country'"
            ):
                if lat is None or lng is None:
                    continue
                norm = _normalize_country(str(name or "")).strip().lower()
                if norm:
                    idx[norm] = (float(lat), float(lng), model or "wos-ref")
            conn.close()
    except Exception:
        pass
    _REF_COUNTRY_NORM_INDEX = idx
    return idx

def _ref_match_tier(tier: str, c1: str) -> Optional[Tuple[str, float, float, str]]:
    """在固定参考库中匹配单条地址的 country / org，命中返回 (名称, lat, lng, model)。

    · org     ：用地址首段（原始机构名）精确查库；
    · country ：先用末段原文精确查库，未命中再用规范化国家名查库内索引。
    显示名统一为规范化国家名 / 原始机构名，与大模型解析结果保持一致。
    """
    key = _tier_ref_key(tier, c1)
    if not key:
        return None
    if tier == "org":
        rec = _affiliation_cache_get(key)
        if rec is not None:
            return key, rec.get("lat"), rec.get("lng"), rec.get("_model") or "wos-ref"
        return None
    if tier == "country":
        rec = _affiliation_cache_get(key)
        if rec is not None:
            return _normalize_country(key), rec.get("lat"), rec.get("lng"), rec.get("_model") or "wos-ref"
        hit = _ref_country_norm_index().get(_normalize_country(key).strip().lower())
        if hit is not None:
            return _normalize_country(key), hit[0], hit[1], hit[2]
    return None

def _tier_rule_parse(tier: str, c1: str) -> Dict:
    """分层解析的规则解析降级方案（AI 不可用时的兜底）"""
    if tier == "country":
        r = {"Country": "", "lat": None, "lng": None}
        parts = c1.split("]", 1)
        addr = parts[1].strip() if len(parts) > 1 else c1
        segs = [s.strip() for s in addr.split(",")]
        if segs:
            country = segs[-1].rstrip(".").strip()
            if country:
                r["Country"] = _normalize_country(country)
                coords = _lookup_country_coords(r["Country"])
                if coords:
                    r["lat"], r["lng"] = coords
    elif tier == "city":
        r = {"City": "", "lat": None, "lng": None}
        parts = c1.split("]", 1)
        addr = parts[1].strip() if len(parts) > 1 else c1
        segs = [s.strip() for s in addr.split(",")]
        # 尝试提取城市：倒数第二或第三段（邮编前一段）
        if len(segs) >= 2:
            r["City"] = segs[-2]
        if len(segs) >= 3 and re.search(r'\d', segs[-2]):
            r["City"] = segs[-3]
    else:  # org
        r = {"Organization": "", "lat": None, "lng": None}
        parts = c1.split("]", 1)
        addr = parts[1].strip() if len(parts) > 1 else c1
        segs = [s.strip() for s in addr.split(",")]
        if segs:
            r["Organization"] = segs[0]
    return r

