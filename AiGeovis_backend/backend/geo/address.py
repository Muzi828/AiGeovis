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

from geo.country import _lookup_country_coords, _normalize_country
from geo.country import _normalize_country

def _field_cols(field: str) -> Dict[str, str]:
    """返回字段名映射：C1 沿用原有列名，其余字段加 {field}_ 前缀。"""
    if field == "C1":
        return {
            "country": "Country/Region",
            "org":     "Organization",
            "city1":   "City1",
            "city2":   "City2",
            "lat":     "Latitude",
            "lng":     "Longitude",
            "src":     "ParseSrc",
            "model":   "ParseModel",
        }
    return {
        "country": f"{field}_Country",
        "org":     f"{field}_Organization",
        "city1":   f"{field}_City1",
        "city2":   f"{field}_City2",
        "lat":     f"{field}_Latitude",
        "lng":     f"{field}_Longitude",
        "src":     f"{field}_ParseSrc",
        "model":   f"{field}_ParseModel",
    }

def _tier_cols(field: str, tier: str) -> Dict[str, str]:
    """分层解析列名，加 field 前缀区分不同字段（C1/C3）"""
    p = f"{field}_"
    return {
        "country": {
            "name": f"{p}Country",
            "lat":  f"{p}Country_Lat",
            "lng":  f"{p}Country_Lng",
            "src":  f"{p}Country_Src",
            "model":f"{p}Country_Model",
        },
        "city": {
            "name": f"{p}City",
            "lat":  f"{p}City_Lat",
            "lng":  f"{p}City_Lng",
            "src":  f"{p}City_Src",
            "model":f"{p}City_Model",
        },
        "org": {
            "name": f"{p}Org",
            "lat":  f"{p}Org_Lat",
            "lng":  f"{p}Org_Lng",
            "src":  f"{p}Org_Src",
            "model":f"{p}Org_Model",
        },
    }[tier]

def _tier_parsed_df_key(field: str, tier: str) -> str:
    return f"parsed_df_{field}_{tier}"

def _field_parsed_df_key(field: str) -> str:
    return f"parsed_df_{field}"

def _get_field_df(sess: Dict, field: str) -> pd.DataFrame:
    """获取指定字段的解析结果表；未解析时回退到原始数据表。"""
    return sess.get(_field_parsed_df_key(field), sess["df"])

def _split_address_cell(value: Any) -> List[str]:
    """将 WoS C1/C3 单元格按分号拆成单条地址。
    先移除 [作者姓名] 前缀（方括号内可能含分号，必须在切割前清除），再按分号拆分。
    """
    if pd.isna(value):
        return []
    raw = str(value).strip()
    if not raw:
        return []
    # 移除所有 [...] 形式的作者前缀（非贪婪，支持括号内含分号的情况）
    raw = re.sub(r'\[.*?\]', '', raw, flags=re.DOTALL)
    return [p.strip() for p in raw.split(";") if p.strip()]

_C3_INST_KEYWORDS = [
    "university", "college", "institute", "school", "hospital", "center",
    "centre", "foundation", "research", "laboratory", "department", "division",
    "faculty", "academy", "system", "ministry", "board", "authority",
    "agency", "bureau", "office", "service", "association", "clinic",
    "innovation", "health", "medical", "science", "technology",
    "engineering", "polytechnic", "consortium", "commission",
]
_C3_INST_PATTERN = re.compile(
    r"^\s*(" + "|".join(_C3_INST_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_C3_INST_PATTERN2 = re.compile(
    r'^"?\s*(' + "|".join(_C3_INST_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

def _split_c3_field(c3_str: str) -> List[str]:
    """
    C3 字段专用拆分规则。

    C3 的原始 WoS 格式为：每个机构一行，多行用缩进延续。
    metaknowledge 的 makeDict() 将其用空格拼接成单字符串。

    拆分策略：在句点后跟机构关键词时拆分，其他句点（缩写如 T.H.）保留。
    对于无句点的情况（如 "University A University B"），不做拆分。
    对于含分号的情况，先按分号拆分，每段再按关键词拆分。
    """
    if not c3_str or not isinstance(c3_str, str):
        return []
    raw = str(c3_str).strip()
    if not raw:
        return []

    def _split_segments(text: str) -> List[str]:
        """按机构关键词模式拆分文本段，返回各机构列表。"""
        # 找到所有 . + 空格 + 机构关键词的位置
        combined = "|".join(_C3_INST_KEYWORDS)
        pattern = r"\. (" + combined + r")\b"
        parts = re.split(pattern, text)
        insts = []
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 检查是否以机构关键词开头
            if _C3_INST_PATTERN.match(part):
                if current:
                    insts.append(current.strip())
                    current = part
                else:
                    current = part
            else:
                if current:
                    current = current + ". " + part
                else:
                    current = part
        if current:
            insts.append(current.strip())
        return [i for i in insts if i]

    # 含分号：分号段分别处理
    if ";" in raw:
        parts = [p.strip() for p in raw.split(";") if p.strip()]
        result: List[str] = []
        for part in parts:
            result.extend(_split_segments(part))
        return result

    # 无分号：直接拆分
    return _split_segments(raw)

def _explode_address_field(df: pd.DataFrame, field: str, keep_index: bool = False) -> pd.DataFrame:
    """按目标字段展开地址行：一条记录中多个地址会变成多条地址记录。

    C3 字段使用专用拆分规则 _split_c3_field，其他字段使用通用的 _split_address_cell。

    参数
    ───
    keep_index : 为 True 时，展开后 DataFrame 的 MultiIndex（level=0）保留原始文献索引，
                 方便后续按文献分组。仅新增接口需要此行为；现有调用均传默认值 False。
    """
    if field not in df.columns or df.empty:
        return df.copy()

    split_fn: Callable[[Any], List[str]] = (
        _split_c3_field if field == "C3" else _split_address_cell
    )

    rows = []
    indices = []
    for orig_idx, row in df.iterrows():
        raw = row.get(field, "")
        if pd.isna(raw) or not str(raw).strip():
            continue
        addresses = split_fn(raw)
        for address in addresses:
            new_row = row.copy()
            new_row[field] = address
            rows.append(new_row)
            indices.append(orig_idx)

    result_df = pd.DataFrame(rows, columns=df.columns)
    if keep_index:
        result_df.index = pd.MultiIndex.from_tuples(
            [(idx, i) for idx, i in zip(indices, range(len(indices)))],
            names=["paper_idx", "addr_idx"],
        )
    else:
        result_df = result_df.reset_index(drop=True)
    return result_df

_INVALID_PLACEHOLDERS = {
    "", "none", "null", "nan", "nat", "n/a", "na", "-", "--", "unknown",
    "undefined", ZH.S_d81bb206a8, ZH.S_f61f4cf6d0, ZH.S_1622dc9b6b,
}

def _is_blank_text(value: Any) -> bool:
    """判定文本字段是否实质为空（兼容 NaN、字符串 "None"/"null" 等占位符）。"""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return True
    return text.lower() in _INVALID_PLACEHOLDERS

def _to_float_or_none(value: Any) -> Optional[float]:
    """安全转换经纬度；空值、占位字符串或非法值统一返回 None。"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        if value.strip().lower() in _INVALID_PLACEHOLDERS:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _is_org_fragment(org: str) -> bool:
    """判断 Organization 是否为残片（不完整的机构名）。"""
    if not org:
        return False
    org_lower = org.lower()

    # 纯单词/过短的片段（1-3个单词且没有实质性机构特征）
    words = org.split()
    if len(words) <= 2 and len(org) <= 25:
        # 常见残片模式：只有 "University"、"University of"、"Technology" 等
        fragment_patterns = [
            r'^university$', r'^university of$', r'^university of the$',
            r'^institute$', r'^college$', r'^school$',
            r'^technology$', r'^engineering$', r'^science$', r'^sciences$',
            r'^medicine$', r'^medical$', r'^health$', r'^hospital$',
            r'^department$', r'^dept$', r'^division$', r'^faculty$',
            r'^laboratory$', r'^lab$', r'^center$', r'^centre$',
            r'^research$', r'^studies$', r'^study$',
        ]
        for pat in fragment_patterns:
            if re.match(pat, org_lower):
                return True

    # 包含明显的残片关键词作为完整名称（没有大学/机构主名）
    orphan_keywords = [
        "department", "dept", "division", "faculty",
        "laboratory", "lab", "center", "centre",
        "institute", "school",
    ]
    for kw in orphan_keywords:
        if org_lower.startswith(kw + " ") or org_lower.startswith(kw + ","):
            return True

    return False

def _sanitize_parse_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """把解析结果中的占位字符串/NaN 统一规范成空值，避免污染 cache 与最终 DataFrame。
    - 文本字段：判空后归一为 ""
    - Organization：对残片（不完整机构名）置为空，触发重试或兜底
    - lat / lng：转 float，越界或为占位符 -> None
    """
    cleaned = dict(result)
    for key in ("Country/Region", "Organization", "City1", "City2"):
        cleaned[key] = "" if _is_blank_text(cleaned.get(key)) else str(cleaned.get(key)).strip()

    # Organization 质量校验：残片置为空
    if _is_org_fragment(cleaned.get("Organization", "")):
        cleaned["Organization"] = ""

    for key in ("lat", "lng"):
        cleaned[key] = _to_float_or_none(cleaned.get(key))

    lat = cleaned.get("lat")
    lng = cleaned.get("lng")
    if lat is not None and not (-90.0 < lat < 90.0):
        cleaned["lat"] = None
    if lng is not None and not (-180.0 < lng < 180.0):
        cleaned["lng"] = None
    return cleaned

def _parse_result_issues(result: Dict[str, Any]) -> List[str]:
    """检查解析结果是否完整；返回问题列表，空列表表示可用。
    判空规则与 `_sanitize_parse_result` 保持一致：占位字符串、NaN、越界经纬度都视为无效。
    """
    issues = []
    required_text = [
        ("Country/Region", ZH.S_887351b33b),
        ("Organization", ZH.S_ff59e30102),
        ("City1", ZH.S_34b18ec132),
        ("City2", ZH.S_b9b3df78b5),
    ]
    for key, message in required_text:
        if _is_blank_text(result.get(key)):
            issues.append(message)

    lat = _to_float_or_none(result.get("lat"))
    lng = _to_float_or_none(result.get("lng"))
    if lat is None or lng is None:
        issues.append(ZH.S_1a2b0de102)
    elif abs(lat) < 1e-9 and abs(lng) < 1e-9:
        # 同时为 0/0 通常是模型给的占位坐标
        issues.append(ZH.S_a20759f68f)
    elif not (-90.0 < lat < 90.0) or not (-180.0 < lng < 180.0):
        issues.append(ZH.S_b31c4aee47)
    return issues

def _c3_result_issues(result: Dict[str, Any]) -> List[str]:
    """检查 C3 解析结果是否完整。

    C3 只需：国家非空 + 机构名非空 + 经纬度有效。
    经纬度由 Nominatim 补救兜底，Organization 不再做残片校验（AI 每次重试都从头解析）。

    例外：参考库命中的结果（_src 以 "db" 开头）只要求机构名 + 有效经纬度——
    C3/机构本身不含国家，库里也只有 机构→坐标，不应因缺国家把库命中判为不完整。
    """
    issues = []
    from_db = str(result.get("_src", "")).startswith("db")

    if not from_db and _is_blank_text(result.get("Country/Region")):
        issues.append(ZH.S_887351b33b)

    if _is_blank_text(result.get("Organization")):
        issues.append(ZH.S_b724de7f8f)

    lat = _to_float_or_none(result.get("lat"))
    lng = _to_float_or_none(result.get("lng"))
    if lat is None or lng is None:
        issues.append(ZH.S_1a2b0de102)
    elif abs(lat) < 1e-9 and abs(lng) < 1e-9:
        issues.append(ZH.S_a20759f68f)
    elif lat is not None and not (-90.0 < lat < 90.0):
        issues.append(ZH.S_12e6cd7bf4)
    elif lng is not None and not (-180.0 < lng < 180.0):
        issues.append(ZH.S_dd81478f85)

    return issues

def rule_parse_c1(c1: str) -> Dict:
    r = {"Country/Region": "", "Organization": "", "City1": "", "City2": "", "lat": None, "lng": None}
    try:
        parts = c1.split("]", 1)
        addr = parts[1].strip() if len(parts) > 1 else c1
        segs = [s.strip() for s in addr.split(",")]
        if segs:
            r["Organization"] = segs[0]
        if len(segs) >= 2:
            r["Country/Region"] = _normalize_country(segs[-1].rstrip("."))
        if len(segs) >= 3:
            r["City2"] = segs[-2]
        if len(segs) >= 4:
            r["City1"] = segs[-3]
    except Exception:
        pass
    return r

def _tier_result_issues(tier: str, result: Dict) -> List[str]:
    """检查分层解析结果是否完整"""
    issues = []
    name_key = {"country": "Country", "city": "City", "org": "Organization"}[tier]
    if _is_blank_text(result.get(name_key)):
        issues.append(f"{name_key}{ZH.S_7085e8f542}")

    lat = _to_float_or_none(result.get("lat"))
    lng = _to_float_or_none(result.get("lng"))
    if lat is None or lng is None:
        issues.append(ZH.S_1a2b0de102)
    elif abs(lat) < 1e-9 and abs(lng) < 1e-9:
        issues.append(ZH.S_a20759f68f)
    elif lat is not None and not (-90.0 < lat < 90.0):
        issues.append(ZH.S_12e6cd7bf4)
    elif lng is not None and not (-180.0 < lng < 180.0):
        issues.append(ZH.S_dd81478f85)
    return issues

