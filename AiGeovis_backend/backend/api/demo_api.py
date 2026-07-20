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


DEMO_GML_FILES = {
    "entity_matrix_C1_country.gml": "demoData/entity_matrix_C1_country.gml",
    "entity_matrix_C1_city.gml": "demoData/entity_matrix_C1_city.gml",
    "entity_matrix_C1_org.gml": "demoData/entity_matrix_C1_org.gml",
    "entity_matrix_C3_org.gml": "demoData/entity_matrix_C3_org.gml",
}

@router.get("/api/demo/gml/download")
def download_demo_gml(filename: str):
    """
    Download a Demo GML file.

    Parameters
    ──────────
    filename : GML file name (required)
               Allowed values:
               - C1CountryMatrix_sample.gml
               - entity_matrix_C1_country.gml
               - entity_matrix_C1_city.gml
               - entity_matrix_C1_org.gml

    Returns
    ───────
    A GML file stream.
    """
    # 验证文件名
    if filename not in DEMO_GML_FILES:
        available = ", ".join(DEMO_GML_FILES.keys())
        raise HTTPException(
            status_code=400,
            detail=f"{ZH.S_09d8095542}{filename}{ZH.S_bf1ad3f2d1}{available}"
        )

    # 获取文件完整路径
    backend_dir = PROJECT_ROOT
    file_path = backend_dir / DEMO_GML_FILES[filename]

    # 检查文件是否存在
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{ZH.S_4a528581a6}{filename}"
        )

    # 读取文件内容
    def iter_file():
        with open(file_path, "r", encoding="utf-8") as f:
            yield f.read()

    # 返回文件流
    return StreamingResponse(
        iter_file(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )

@router.get("/api/demo/gml/list")
def list_demo_gml_files():
    """
    List all downloadable Demo GML files.

    Returns
    ───────
    File list information.
    """
    backend_dir = PROJECT_ROOT
    files_info = []

    for key, relative_path in DEMO_GML_FILES.items():
        file_path = backend_dir / relative_path
        file_info = {
            "filename": key,
            "exists": file_path.exists(),
            "size_bytes": file_path.stat().st_size if file_path.exists() else None,
        }
        files_info.append(file_info)

    return {"files": files_info}

DEMO_DATA_DIR = PROJECT_ROOT / "demoData"

@router.get("/api/demo/data/{filename}")
def get_demo_data(filename: str):
    """
    Generic endpoint to fetch JSON data from the demoData directory by file name.
    e.g. GET /api/demo/data/demoList
         GET /api/demo/data/demoC1CityCount
    """
    if not filename.endswith(".json"):
        filename += ".json"
    file_path = DEMO_DATA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{ZH.S_3e70c2d15e}{filename}{ZH.S_5095e98c51}")
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

@router.get("/api/demo/files")
def list_demo_files():
    """List all available data files in the demoData directory."""
    if not DEMO_DATA_DIR.exists():
        raise HTTPException(status_code=404, detail=ZH.S_6437879a45)
    files = [f.stem for f in DEMO_DATA_DIR.iterdir() if f.is_file() and f.suffix == ".json"]
    return {"files": sorted(files)}

_CUSTOM_DEMO_FILE = "customDemoAddresses.csv"

@router.post("/api/demo/custom-session")
def create_custom_demo_session():
    """
    Custom data example: load the built-in sample address table (already includes
    coordinates) and create a real session. The parse result table and
    visualizations are ready to use without clicking "Start parsing".
    """
    csv_path = DEMO_DATA_DIR / _CUSTOM_DEMO_FILE
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"{ZH.S_7048c7a378}{_CUSTOM_DEMO_FILE}")

    try:
        table = _read_local_table(csv_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{ZH.S_f204cee7ee}{e}")

    if table.empty:
        raise HTTPException(status_code=500, detail=ZH.S_6115ab046e)

    table.columns = [str(c).strip() for c in table.columns]
    name_col = None
    for col in table.columns:
        if str(col).lower().strip() in _LOCAL_ADDR_NAME_HINTS:
            name_col = col
            break
    if name_col is None:
        name_col = table.columns[0]

    count_col = None
    for col in table.columns:
        if col == name_col:
            continue
        low = str(col).lower().strip()
        if any(h in low for h in _LOCAL_ADDR_COUNT_HINTS):
            count_col = col
            break

    lat_col = next((c for c in table.columns if str(c).lower().strip() in ("lat", "latitude", ZH.S_6acaee71fe)), None)
    lng_col = next((c for c in table.columns if str(c).lower().strip() in ("lng", "lon", "long", "longitude", ZH.S_3d18ca01dd)), None)

    names = table[name_col].astype(str).str.strip()
    if count_col is not None:
        counts = pd.to_numeric(
            table[count_col].astype(str).str.strip().str.replace(",", ""),
            errors="coerce",
        ).fillna(1).astype(int)
    else:
        counts = pd.Series([1] * len(table), dtype=int)

    if lat_col is not None:
        lats = pd.to_numeric(table[lat_col], errors="coerce")
    else:
        lats = pd.Series([np.nan] * len(table), dtype=float)
    if lng_col is not None:
        lngs = pd.to_numeric(table[lng_col], errors="coerce")
    else:
        lngs = pd.Series([np.nan] * len(table), dtype=float)

    mask = names.ne("") & ~names.str.lower().isin(("nan", "none"))
    names = names[mask].reset_index(drop=True)
    counts = counts[mask].reset_index(drop=True)
    lats = lats[mask].reset_index(drop=True)
    lngs = lngs[mask].reset_index(drop=True)

    has_coords = bool(lats.notna().any() and lngs.notna().any())

    df = pd.DataFrame({
        "Organization": names.values,
        "lat": lats.values,
        "lng": lngs.values,
        "count": counts.values,
        "ParseSrc": "demo" if has_coords else "pending",
        "ParseModel": "demo-coords" if has_coords else "",
        "_affiliation_type": "affiliation_org",
    })

    empty_country = pd.DataFrame(columns=["Country/Region", "lat", "lng", "count", "ParseSrc", "ParseModel"])
    empty_city = pd.DataFrame(columns=["City1", "lat", "lng", "count", "ParseSrc", "ParseModel"])
    parsed_org = pd.DataFrame({
        "Organization": df["Organization"].values,
        "lat": df["lat"].values,
        "lng": df["lng"].values,
        "count": df["count"].values,
        "ParseSrc": df["ParseSrc"].values,
        "ParseModel": df["ParseModel"].values,
    }) if has_coords else pd.DataFrame(
        columns=["Organization", "lat", "lng", "count", "ParseSrc", "ParseModel"]
    )

    sid = uuid.uuid4().hex
    sessions[sid] = {
        "df":                              df,
        "file_type":                       "affiliation",
        "source_type":                     "local_address",
        "affiliation_subtypes":             ["affiliation_org"],
        "parsed_df_affiliation_country":    empty_country.copy(),
        "parsed_df_affiliation_org":        parsed_org,
        "parsed_df_affiliation_city":       empty_city.copy(),
        "tmp_dir":                         "",
        "record_count":                    len(df),
        "loaded_at":                       time_module.time(),
        "pre_parsed":                      has_coords,
    }

    return {
        "session_id":   sid,
        "record_count": len(df),
        "columns":      ["name", "count", "lat", "lng"] if has_coords else ["name", "count"],
        "files":        [_CUSTOM_DEMO_FILE],
        "file_type":    "affiliation",
        "source_type":  "local_address",
        "affiliation_subtypes": ["affiliation_org"],
        "pre_parsed":   has_coords,
    }

