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


@router.post("/api/geo/geocode")
def run_geocode(req: GeocodeRequest):
    """Deterministic geocoding fallback (Nominatim / AMap): fill in coordinates for
    entries still missing them after parsing, and write the results back into the
    parse result table."""
    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    # ── affiliation 会话：直接对三个子类型表做兜底回填 ──
    if sess.get("file_type") == "affiliation":
        return _geocode_affiliation_session(sess, req.amap_key, req.use_nominatim)

    # ── 分层解析表兜底（HomeView 的 parse-batch-tiers 产物）──
    if req.tier in ("country", "city", "org"):
        tier_key = _tier_parsed_df_key(req.field, req.tier)
        tdf = sess.get(tier_key)
        tcols = _tier_cols(req.field, req.tier)
        if tdf is None or tcols["name"] not in tdf.columns:
            raise HTTPException(status_code=400, detail=f"{ZH.S_a9d3a66867}{req.field}/{req.tier}{ZH.S_aabffa5576}")

        cache: Dict[str, Optional[Dict[str, float]]] = {}
        items = []
        filled = 0
        checked = 0
        for idx, row in tdf.iterrows():
            if not _coord_missing(row.get(tcols["lat"]), row.get(tcols["lng"])):
                continue
            name = str(row.get(tcols["name"], "") or "").strip()
            if not name:
                continue
            checked += 1
            coords = _geocode_query(name, req.amap_key, req.use_nominatim, cache)
            if not coords:
                continue
            tdf.at[idx, tcols["lat"]] = coords["lat"]
            tdf.at[idx, tcols["lng"]] = coords["lng"]
            tdf.at[idx, tcols["src"]] = "geocode"
            tdf.at[idx, tcols["model"]] = coords.get("provider", "nominatim")
            filled += 1
            items.append({"query": name, "lat": coords["lat"], "lng": coords["lng"]})
        sess[tier_key] = tdf
        return {"total": len(items), "checked": checked, "filled": filled,
                "items": items, "field": req.field, "tier": req.tier}

    parsed_key = _field_parsed_df_key(req.field)
    df = sess.get(parsed_key)
    cols = _field_cols(req.field)
    if df is None or cols["country"] not in df.columns:
        raise HTTPException(status_code=400, detail=f"{ZH.S_a9d3a66867}{req.field}{ZH.S_49b3810efc}")

    lat_col, lng_col = cols["lat"], cols["lng"]
    src_col, model_col = cols["src"], cols["model"]
    for c in (lat_col, lng_col):
        if c not in df.columns:
            df[c] = np.nan
    for c in (src_col, model_col):
        if c not in df.columns:
            df[c] = ""

    geocode_cache: Dict[str, Optional[Dict[str, float]]] = {}
    results = []
    filled = 0
    checked = 0

    for idx, row in df.iterrows():
        if not _coord_missing(row.get(lat_col), row.get(lng_col)):
            continue
        country = str(row.get(cols["country"], "") or "").strip()
        city    = str(row.get(cols["city1"], "") or "").strip()
        org     = str(row.get(cols["org"], "") or "").strip()

        if city and country:
            query = f"{city}, {country}"
        elif org and country:
            query = f"{org}, {country}"
        elif country:
            query = country
        elif org:
            query = org
        else:
            continue

        checked += 1
        coords = _geocode_query(query, req.amap_key, req.use_nominatim, geocode_cache)
        if not coords:
            continue
        df.at[idx, lat_col] = coords["lat"]
        df.at[idx, lng_col] = coords["lng"]
        df.at[idx, src_col] = "geocode"
        df.at[idx, model_col] = coords.get("provider", "nominatim")
        filled += 1
        results.append({
            "country": country, "city": city,
            "organization": org, "query": query,
            "lat": coords["lat"], "lng": coords["lng"],
        })

    sess[parsed_key] = df
    sess[f"geocode_items_{req.field}"] = results

    return {"total": len(results), "checked": checked, "filled": filled,
            "items": results, "field": req.field}

