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
from datetime import datetime
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


@router.get("/api/geo/entity-matrix")
def get_entity_matrix(
    session_id: str,
    field: str = "C1",
    tier: str = "country",
    top_n: int = 50,
    threshold: int = 0,
):
    """
    Organization / city / country co-occurrence matrix (generic version).

    Based on the parsed tier data, aggregate the deduplicated set of entities per
    paper, compute the pairwise co-occurrence matrix, and return the coordinates
    of each entity.

    Parameters
    ──────────
    session_id : session ID (required)
    field      : field name, default C1 (supports C1 / C3)
    tier       : analysis tier, default country
                 - country : use the country name directly (China, United States ...)
                 - city    : use "Country > City" format (China > Beijing ...)
                 - org     : use "Country > Org" format (China > Chinese Acad Sci ...)
    top_n      : maximum number of entities included in the matrix, default 50
    threshold  : minimum co-occurrence count; edges below this are omitted, default 0 (return all)

    Returns
    ───────
    entities              : list of entity names (matrix row/column order)
    matrix                : n x n co-occurrence matrix; the diagonal is the paper count for that entity
    nodes                 : list of entity nodes (with frequency and coordinates)
    edges                 : list of co-occurrence edges (already filtered by threshold)
    total_papers          : total number of papers
    papers_with_entity    : number of papers that have entity info for this tier
    papers_without_entity : number of papers without entity info for this tier
    total_pairs           : accumulated weight of all co-occurrence pairs
    """
    if tier not in ("country", "city", "org"):
        raise HTTPException(status_code=400, detail=ZH.S_7cdc1fa367)

    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)

    paper_entities, entity_coords = (
        _aggregate_unified_c3_entities(sess, tier)
        if field == "C3"
        else _aggregate_paper_entities(sess, field, tier)
    )

    if not paper_entities:
        detail = (
            f"{ZH.S_ea157063a0}{field}{ZH.S_8e5767e2c0}"
            if field == "C3"
            else f"{ZH.S_ea157063a0}{field} tier={tier}{ZH.S_e5cb77dc43}{tier}{ZH.S_59d76cf338}"
        )
        raise HTTPException(
            status_code=400,
            detail=detail
        )

    result = _build_entity_matrix(paper_entities, entity_coords, top_n=top_n, threshold=threshold)
    result["session_id"] = session_id
    result["field"] = field
    result["tier"] = tier
    return result

@router.get("/api/geo/country-matrix")   # legacy endpoint name, kept for backward compatibility
def get_country_matrix(
    session_id: str,
    field: str = "C1",
    top_n: int = 50,
    threshold: int = 0,
):
    """[Compatibility alias] Equivalent to GET /api/geo/entity-matrix?tier=country."""
    return get_entity_matrix(
        session_id=session_id,
        field=field,
        tier="country",
        top_n=top_n,
        threshold=threshold,
    )

@router.get("/api/geo/entity-matrix/export")
def export_entity_matrix_gml(
    session_id: str,
    field: str = "C1",
    tier: str = "country",
    top_n: int = 50,
    threshold: int = 0,
    coord_type: str = "normalized",
    include_matrix: bool = False,
):
    """
    Export entity-matrix data as a GML (Gephi Graph Modeling Language) file.

    Parameters
    ──────────
    session_id     : session ID (required)
    field          : field name, default C1 (supports C1 / C3)
    tier           : analysis tier, default country (country / city / org)
    top_n          : maximum number of entities included in the matrix, default 50
    threshold      : minimum co-occurrence count, default 0
    coord_type     : coordinate type
                     - normalized : normalized to [-1, 1] (suited for network visualization)
                     - geo       : use latitude/longitude (suited for geographic visualization)
                     - none      : do not output coordinates
    include_matrix : whether to include the adjacency matrix in comments, default false

    Returns
    ───────
    A GML file stream.
    """
    # 验证参数
    if tier not in ("country", "city", "org"):
        raise HTTPException(status_code=400, detail=ZH.S_7cdc1fa367)
    if coord_type not in ("normalized", "geo", "none"):
        raise HTTPException(status_code=400, detail=ZH.S_e4c855fdeb)

    # 获取 entity-matrix 数据
    matrix_data = get_entity_matrix(
        session_id=session_id,
        field=field,
        tier=tier,
        top_n=top_n,
        threshold=threshold,
    )

    # 生成 GML 内容
    gml_content = _generate_gml(
        nodes=matrix_data["nodes"],
        edges=matrix_data["edges"],
        coord_type=coord_type,
        include_matrix=include_matrix,
        matrix=matrix_data["matrix"],
        entities=matrix_data["entities"],
    )

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"entity_matrix_{tier}_{timestamp}.gml"

    # 返回文件流
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([gml_content]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )

