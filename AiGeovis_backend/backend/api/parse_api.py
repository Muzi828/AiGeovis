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


@router.post("/api/geo/parse-c1")
def start_parse_c1(req: ParseC1Request, background_tasks: BackgroundTasks):
    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    df = sess["df"]
    field = req.field if req.field in ("C1", "C3") else "C1"
    if field not in df.columns:
        raise HTTPException(status_code=400, detail=f"{ZH.S_0045f05cd5}{field}{ZH.S_fa972a917d}")
    if not req.ai_configs:
        raise HTTPException(status_code=400, detail=ZH.S_dbcdc2ee01)

    # 重置停止标志
    stop_flags[req.session_id] = threading.Event()

    parse_progress[req.session_id] = {
        "status": "running",
        "progress": 0,
        "logs": [_tr(req.lang,
                     f"{ZH.S_a865e2e99a}{field}{ZH.S_5e08e1c379}{len(req.ai_configs)}{ZH.S_8d9a243412}",
                     f"Starting parse (field: {field}) with {len(req.ai_configs)} model(s)...")],
    }
    background_tasks.add_task(
        _bg_parse_c1, req.session_id, df.copy(), req.ai_configs, req.batch_size, field,
        req.skip_cache, req.lang,
    )
    return {"message": ZH.S_8086bdef9b, "session_id": req.session_id, "field": field}

@router.post("/api/geo/parse-tier")
def start_parse_tier(req: ParseTierRequest, background_tasks: BackgroundTasks):
    """Tiered parse: parse country / city / organization independently. C1 field only."""
    if req.tier not in ("country", "city", "org"):
        raise HTTPException(status_code=400, detail=ZH.S_7cdc1fa367)
    if req.field == "C3":
        raise HTTPException(status_code=400, detail=ZH.S_29062f71e8)

    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    df = sess["df"]
    field = req.field if req.field in ("C1", "C3") else "C1"
    if field not in df.columns:
        raise HTTPException(status_code=400, detail=f"{ZH.S_0045f05cd5}{field}{ZH.S_fa972a917d}")
    if not req.ai_configs:
        raise HTTPException(status_code=400, detail=ZH.S_dbcdc2ee01)

    tier_lbl = _tier_label(req.tier, req.lang)
    tier_key = f"{req.session_id}_{req.tier}"

    # 新结构：每个 session 下的 tiers 字典（兼容 parse-c1 写入的旧结构）
    if req.session_id not in parse_progress:
        parse_progress[req.session_id] = {"tiers": {}, "overall_status": "running"}
    elif "tiers" not in parse_progress[req.session_id]:
        parse_progress[req.session_id] = {"tiers": {}, "overall_status": "running"}
    parse_progress[req.session_id]["tiers"][req.tier] = {
        "status": "running",
        "progress": 0,
        "logs": [_tr(req.lang,
                     f"{ZH.S_1fce799168}{tier_lbl}{ZH.S_b24791a1db}{field}{ZH.S_5e08e1c379}{len(req.ai_configs)}{ZH.S_8d9a243412}",
                     f"Starting {tier_lbl} parse (field: {field}) with {len(req.ai_configs)} model(s)...")],
    }
    stop_flags[tier_key] = threading.Event()
    background_tasks.add_task(
        _bg_parse_tier, req.session_id, df.copy(), req.ai_configs,
        req.batch_size, field, req.tier, bool(req.skip_cache), req.lang
    )
    return {"message": _tr(req.lang, f"{tier_lbl}{ZH.S_8086bdef9b}", f"{tier_lbl} parse started"),
            "session_id": req.session_id, "field": field, "tier": req.tier, "skip_cache": bool(req.skip_cache)}

@router.post("/api/geo/parse-batch-tiers")
def start_parse_batch_tiers(req: ParseBatchTiersRequest, background_tasks: BackgroundTasks):
    """Batch tiered parse: start multiple tier parses at once, running in parallel."""
    valid_tiers = {"country", "city", "org"}
    requested = set(req.tiers)
    invalid = requested - valid_tiers
    if invalid:
        raise HTTPException(status_code=400, detail=f"{ZH.S_2991832520}{invalid}{ZH.S_b08afc8493}")
    if req.field == "C3":
        raise HTTPException(status_code=400, detail=ZH.S_29062f71e8)

    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    df = sess["df"]
    field = req.field if req.field in ("C1", "C3") else "C1"
    if field not in df.columns:
        raise HTTPException(status_code=400, detail=f"{ZH.S_0045f05cd5}{field}{ZH.S_fa972a917d}")
    if not req.ai_configs:
        raise HTTPException(status_code=400, detail=ZH.S_dbcdc2ee01)
    if not req.tiers:
        raise HTTPException(status_code=400, detail=ZH.S_d7a4491ea4)

    # 初始化进度结构（确保新旧结构兼容）
    if req.session_id not in parse_progress:
        parse_progress[req.session_id] = {"tiers": {}, "overall_status": "running"}
    elif "tiers" not in parse_progress[req.session_id]:
        parse_progress[req.session_id] = {"tiers": {}, "overall_status": "running"}

    for tier in req.tiers:
        tier_key = f"{req.session_id}_{tier}"
        tier_lbl = _tier_label(tier, req.lang)
        parse_progress[req.session_id]["tiers"][tier] = {
            "status": "running",
            "progress": 0,
            "logs": [_tr(req.lang,
                         f"{ZH.S_1fce799168}{tier_lbl}{ZH.S_b24791a1db}{field}{ZH.S_5e08e1c379}{len(req.ai_configs)}{ZH.S_8d9a243412}",
                         f"Starting {tier_lbl} parse (field: {field}) with {len(req.ai_configs)} model(s)...")],
        }
        stop_flags[tier_key] = threading.Event()
        # 每个 tier 在独立后台线程中并行执行
        background_tasks.add_task(
            _bg_parse_tier, req.session_id, df.copy(), req.ai_configs,
            req.batch_size, field, tier, bool(req.skip_cache), req.lang
        )

    labels = ", ".join(_tier_label(t, req.lang) for t in req.tiers)
    return {
        "message": _tr(req.lang,
                       f"{ZH.S_72106d8e57}{len(req.tiers)}{ZH.S_f405767eca}{labels}",
                       f"Started {len(req.tiers)} tier parse(s): {labels}"),
        "session_id": req.session_id,
        "field": field,
        "tiers": req.tiers,
        "skip_cache": bool(req.skip_cache),
    }

@router.post("/api/geo/parse-affiliation")
def start_parse_affiliation(req: ParseAffiliationRequest, background_tasks: BackgroundTasks):
    """AI parse for affiliation-type files: parse all subtypes (country / organization / city) in one pass."""
    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    if sess.get("file_type") != "affiliation":
        raise HTTPException(status_code=400, detail=ZH.S_679f8f1fe8)

    df_merged = sess["df"]
    if not req.ai_configs:
        raise HTTPException(status_code=400, detail=ZH.S_dbcdc2ee01)

    stop_flags[req.session_id] = threading.Event()
    subtypes = ["affiliation_country", "affiliation_org", "affiliation_city"]
    parse_progress[req.session_id] = {"tiers": {}, "status": "running", "progress": 0, "logs": []}
    for st in subtypes:
        parse_progress[req.session_id]["tiers"][st] = {
            "status": "running", "progress": 0, "logs": []
        }

    background_tasks.add_task(
        _bg_parse_affiliation, req.session_id, df_merged.copy(),
        req.ai_configs, req.batch_size, bool(req.skip_cache), req.lang
    )
    return {"message": _tr(req.lang, ZH.S_8086bdef9b, "Parse started"),
            "session_id": req.session_id, "skip_cache": bool(req.skip_cache)}

@router.post("/api/geo/stop-parse")
def stop_parse(session_id: str, lang: str = "zh"):
    p = parse_progress.get(session_id)
    if not p:
        raise HTTPException(status_code=404, detail=ZH.S_c55621865c)

    stopping_log = _tr(lang, ZH.S_57730c7510,
                       "⏹ Stopping, waiting for the current request to finish...")

    # 批量分层模式：停止所有 tier
    if "tiers" in p:
        for tier, tier_data in p["tiers"].items():
            tier_key = f"{session_id}_{tier}"
            ev = stop_flags.get(tier_key)
            if ev:
                ev.set()
            if tier_data.get("status") == "running":
                tier_data["status"] = "stopping"
                tier_data["logs"].append(stopping_log)
        p["overall_status"] = "stopping"
        return {"message": _tr(lang, ZH.S_6d1f6b1a29,
                               "Stop signal sent to all tiers")}

    # 统一解析 / 旧模式
    ev = stop_flags.get(session_id)
    if not ev:
        raise HTTPException(status_code=404, detail=ZH.S_c55621865c)
    ev.set()
    if p.get("status") == "running":
        p["status"] = "stopping"
        p["logs"] = p.get("logs", []) + [stopping_log]
    return {"message": _tr(lang, ZH.S_e9eda06f8b, "Stop signal sent")}

@router.get("/api/geo/parse-progress")
def get_parse_progress(session_id: str):
    p = parse_progress.get(session_id)
    if not p:
        raise HTTPException(status_code=404, detail=ZH.S_7d8d95d685)

    # 批量分层模式：返回每个 tier 的独立状态 + 聚合状态
    if "tiers" in p:
        tiers = p.get("tiers", {})
        tier_statuses = [t["status"] for t in tiers.values()]

        if "error" in tier_statuses:
            overall = "error"
        elif all(s == "done" for s in tier_statuses):
            overall = "done"
        elif any(s == "stopped" for s in tier_statuses) and not any(s == "running" for s in tier_statuses):
            overall = "stopped"
        elif any(s == "stopping" for s in tier_statuses):
            overall = "stopping"
        else:
            overall = "running"

        overall_progress = 0
        if tiers:
            overall_progress = int(sum(t["progress"] for t in tiers.values()) / len(tiers))

        return {
            "overall_status": overall,
            "overall_progress": overall_progress,
            # 完整返回日志，避免前端解析窗口只显示末尾若干行、旧日志被覆盖
            "logs": list(p.get("logs", []) or []),
            "tiers": {
                tier: {
                    "status": t["status"],
                    "progress": t["progress"],
                    "report": t.get("report", {}),
                    "logs": list(t.get("logs", []) or []),
                }
                for tier, t in tiers.items()
            },
            "report": p.get("report", {}),
        }

    # 统一解析 / 旧模式（向后兼容 C3 统一解析）
    return {
        "status": p["status"],
        "progress": p["progress"],
        "logs": list(p.get("logs", []) or []),
        "report": p.get("report", {}),
    }

