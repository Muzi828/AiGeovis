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
from data_service import DataService

_ds_lock = threading.Lock()
_ds_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ds_loader")

def _load_with_dataservice(path: str, is_dir: bool = False) -> pd.DataFrame:
    """同步版本，在线程池中执行（阻塞操作，不能在 async 事件循环直接调用）。"""
    with _ds_lock:
        svc = DataService()
        if is_dir:
            svc.load_directory(path)
        else:
            svc.load_file(path)
        return svc.get_dataframe()

async def _load_with_dataservice_async(path: str, is_dir: bool = False) -> pd.DataFrame:
    """异步包装：将阻塞的 DataService 加载放入线程池，不阻塞事件循环。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_ds_executor, _load_with_dataservice, path, is_dir)

def _detect_affiliation_subtype(first_line: str, filename: str) -> str:
    """
    根据首行内容检测 affiliation 的子类型。
    返回 "affiliation_country" | "affiliation_org" | "affiliation_city"。
    """
    line = first_line.strip()
    lower_line = line.lower()

    # Countries/Regions → 国家
    if "countries/regions" in lower_line:
        return "affiliation_country"
    # Affiliation with Department → 机构（包含院系信息的机构名称）
    if "affiliation with department" in lower_line:
        return "affiliation_org"
    # Affiliations → 机构（默认）
    if "affiliations" in lower_line:
        return "affiliation_org"

    # 文件名兜底
    fname_lower = filename.lower()
    if "country" in fname_lower:
        return "affiliation_country"
    if "department" in fname_lower:
        return "affiliation_org"
    if "affiliation" in fname_lower:
        return "affiliation_org"

    return "affiliation_org"

def _detect_file_type(first_line: str, filename: str) -> str:
    """
    根据首行内容和文件名检测文件类型。
    返回 "wos" 或 "affiliation_country" / "affiliation_org" / "affiliation_city"。
    """
    line = first_line.strip()
    lower_line = line.lower()

    # affiliation 特征：TSV 三列，列名含 Countries/Regions 或 Affiliations
    if "\t" in line:
        cols = line.split("\t")
        if len(cols) >= 2:
            # 检查列名是否匹配 affiliation 特征
            header_keywords = ["countries/regions", "affiliations", "affiliation with department",
                              "record count", "% of"]
            matched = sum(1 for kw in header_keywords if kw in lower_line)
            if matched >= 1:
                return _detect_affiliation_subtype(first_line, filename)
            # 或者列名第二列是纯数字（数量列），也视为 affiliation
            if len(cols) >= 3 and cols[1].strip().isdigit():
                return _detect_affiliation_subtype(first_line, filename)

    # 也可通过文件名判断
    fname_lower = filename.lower()
    if "affiliation" in fname_lower or "country" in fname_lower:
        return _detect_affiliation_subtype(first_line, filename)

    # 默认走 WoS/BP 解析
    return "wos"

def _parse_affiliation_file(tmp_dir: str, filename: str) -> pd.DataFrame:
    """
    解析 affiliation 类型文件（TSV：名称 + 数量）。
    支持 Countries.txt、Affiliations.txt、Affiliation with Department.txt 等格式。
    """
    file_path = Path(tmp_dir) / filename
    try:
        # 尝试 TSV 格式（制表符分隔）
        df = pd.read_csv(file_path, sep="\t", header=0, dtype=str, encoding="utf-8")
    except Exception:
        try:
            # 回退：尝试逗号分隔
            df = pd.read_csv(file_path, sep=",", header=0, dtype=str, encoding="utf-8")
        except Exception:
            raise ValueError(f"{ZH.S_ba3f36d69c}{filename}{ZH.S_fd89e9bd29}")

    # 清理列名（去除首尾空白）
    df.columns = df.columns.str.strip()

    # 找到名称列和数量列
    name_col = None
    count_col = None

    # 尝试自动匹配列名
    for col in df.columns:
        col_lower = col.lower().strip()
        if name_col is None and ("countries/regions" in col_lower or "affiliation" in col_lower
                                  or col_lower == "affiliations"):
            name_col = col
        elif count_col is None and ("record count" in col_lower or "count" in col_lower):
            count_col = col

    # 如果列名匹配失败，按列顺序推断（第1列=名称，第2列=数量）
    if name_col is None or count_col is None:
        col_list = list(df.columns)
        if len(col_list) >= 2:
            name_col = col_list[0]
            count_col = col_list[1]

    if name_col is None or count_col not in df.columns:
        raise ValueError(f"{ZH.S_13bdf5c2bc}{list(df.columns)}")

    # 构建标准化 DataFrame
    result = pd.DataFrame()
    result["name"] = df[name_col].astype(str).str.strip()
    result["count"] = pd.to_numeric(df[count_col].astype(str).str.strip().str.replace(",", ""), errors="coerce")

    # 过滤掉 footer 行：name 列含 "record(s)" 或 count 无法解析为数字的行
    result = result[
        result["name"].str.contains("record\\(s\\)", case=False, na=False) == False
    ]
    result["count"] = result["count"].fillna(0).astype(int)

    # 去除空行和 name 为空的行
    result = result[result["name"].str.strip().ne("")]
    result = result.reset_index(drop=True)

    return result

_LOCAL_ADDR_EXTS = (".csv", ".xlsx", ".xls")

# 地址列候选名（不区分大小写）；未命中时取第一列（与桌面版行为一致）
_LOCAL_ADDR_NAME_HINTS = (
    "unit-name", "unit_name", "unitname", "address", "addr",
    "affiliation", "institution", "organization", "org", "name",
    ZH.S_7650487a87, ZH.S_f2996845b6, ZH.S_ccfbe706fe, ZH.S_b77053aabc, ZH.S_894dfcd42b,
)
_LOCAL_ADDR_COUNT_HINTS = (
    "record count", "count", "frequency", "freq",
    ZH.S_b73d9d3bc2, ZH.S_41461fa09f, ZH.S_0bf60b32f9, ZH.S_ac1b29a02d,
)
# 国家列候选名（精确匹配，不区分大小写）；命中则额外产出国家子类型并查库
_LOCAL_ADDR_COUNTRY_HINTS = (
    "country", "country/region", "country / region", "countries/regions",
    "nation", ZH.S_ee3f5585b1, ZH.S_39c7b31e48, ZH.S_f6d7e82e7e, ZH.S_2560b304e6,
)

def _read_text_with_fallback(file_path: Path) -> str:
    """读取文本文件，自动尝试常见编码。"""
    raw = file_path.read_bytes()
    last_err: Optional[Exception] = None
    for enc in ("utf-8-sig", "gbk", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError) as e:
            last_err = e
    raise ValueError(f"{ZH.S_924f26926c}{file_path.name} ({last_err})")

def _read_local_table(file_path: Path) -> pd.DataFrame:
    """读取本地 CSV/XLSX 为 DataFrame。

    CSV 特殊处理：若表头只有一列（纯地址列表），逐行手工解析，
    避免未加引号的 "机构, 国家" 地址被 pandas 误拆成多列。
    """
    import csv as csv_lib
    import io as io_lib

    suffix = file_path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(file_path, dtype=str)

    text = _read_text_with_fallback(file_path)
    rows = list(csv_lib.reader(io_lib.StringIO(text)))
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        raise ValueError(f"{ZH.S_5380e4315a}{file_path.name}")

    header = [c.strip() for c in rows[0]]
    if len(header) == 1:
        # 单列地址列表：把每行的所有字段重新拼回完整地址
        values = [", ".join(c.strip() for c in r if str(c).strip()) for r in rows[1:]]
        return pd.DataFrame({header[0]: values}, dtype=str)

    return pd.read_csv(io_lib.StringIO(text), dtype=str)

def _parse_local_address_file(tmp_dir: str, filename: str) -> pd.DataFrame:
    """
    解析本地地址文件（CSV/XLSX）为标准表：name(机构/地址)、count[、lat、lng、country]。
    对应桌面版 DataView 本地模式：默认第一列为地址列；
    若存在数量列（Record Count / 频次等）则一并读取，否则 count=1。
    若存在经纬度列则一并返回（lat/lng），供上传后直接可视化。
    若存在国家列（Country / 国家 等）则额外返回 country 列，供上传后拆出国家子类型并查库。
    """
    df = _read_local_table(Path(tmp_dir) / filename)
    if df.empty or len(df.columns) == 0:
        raise ValueError(f"{ZH.S_5380e4315a}{filename}")
    df.columns = [str(c).strip() for c in df.columns]

    # 先定位数量列、经纬度列、国家列，避免它们被误当作机构地址列
    lat_col = next((c for c in df.columns if str(c).lower().strip() in ("lat", "latitude", ZH.S_6acaee71fe)), None)
    lng_col = next((c for c in df.columns if str(c).lower().strip() in ("lng", "lon", "long", "longitude", ZH.S_3d18ca01dd)), None)
    country_col = next(
        (c for c in df.columns if str(c).lower().strip() in _LOCAL_ADDR_COUNTRY_HINTS),
        None,
    )
    count_col = next(
        (c for c in df.columns
         if any(h in str(c).lower().strip() for h in _LOCAL_ADDR_COUNT_HINTS)),
        None,
    )
    reserved = {c for c in (lat_col, lng_col, country_col, count_col) if c is not None}

    # 机构/地址列：优先命中名称候选（排除已占用列），否则取第一个未占用列
    name_col = None
    for col in df.columns:
        if col in reserved:
            continue
        if str(col).lower().strip() in _LOCAL_ADDR_NAME_HINTS:
            name_col = col
            break
    if name_col is None:
        name_col = next((c for c in df.columns if c not in reserved), None)

    if name_col is None and country_col is None:
        raise ValueError(f"{ZH.S_04b77d7006}{filename}")

    result = pd.DataFrame(index=df.index)
    if name_col is not None:
        result["name"] = df[name_col].astype(str).str.strip()
    if country_col is not None:
        result["country"] = df[country_col].astype(str).str.strip()

    if count_col is not None:
        result["count"] = pd.to_numeric(
            df[count_col].astype(str).str.strip().str.replace(",", ""),
            errors="coerce",
        ).fillna(1).astype(int)
    else:
        result["count"] = 1

    result["lat"] = pd.to_numeric(df[lat_col], errors="coerce") if lat_col is not None else np.nan
    result["lng"] = pd.to_numeric(df[lng_col], errors="coerce") if lng_col is not None else np.nan

    # 至少要有机构名或国家名之一为有效值
    def _clean_mask(col: str) -> pd.Series:
        s = result[col].astype(str).str.strip()
        return s.ne("") & ~s.str.lower().isin(("nan", "none"))

    keep = pd.Series(False, index=result.index)
    if "name" in result.columns:
        keep = keep | _clean_mask("name")
    if "country" in result.columns:
        keep = keep | _clean_mask("country")
    result = result[keep].reset_index(drop=True)
    if result.empty:
        raise ValueError(f"{ZH.S_614b8788f4}{filename}")
    return result

