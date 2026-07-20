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


@router.post("/api/models/list")
def list_models(req: ListModelsRequest):
    """
    Request the model list from the given API endpoint. Supports:
    - OpenAI-compatible (GET /models)
    - Ollama (GET /api/tags or /v1/models)
    - Gemini (returns a fixed list of common models)
    """
    headers = {"Content-Type": "application/json"}

    # Gemini 不支持列表接口，返回常用模型
    if req.provider == "Gemini":
        models = [
            "gemini-2.0-flash", "gemini-2.0-flash-lite",
            "gemini-1.5-flash", "gemini-1.5-pro",
        ]
        return {"models": models}

    # 构建 base_url
    tmp = AIConfig(type=req.type, provider=req.provider,
                   api_key=req.api_key, base_url=req.base_url)
    base = _resolve_base_url(tmp)

    # Anthropic：专用模型列表接口（x-api-key 认证）
    if req.provider == "Anthropic":
        try:
            r = req_lib.get(f"{base}/v1/models", params={"limit": 100},
                            headers=_anthropic_headers(req.api_key), timeout=15)
            r.raise_for_status()
            ids = [m.get("id", "") for m in r.json().get("data", [])]
            return {"models": sorted(filter(None, ids))}
        except Exception as e:
            raise HTTPException(status_code=502,
                                detail=f"{ZH.S_e9fbbc88d6}{str(e)[:200]}")

    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"

    # Ollama 兼容：先尝试标准 /v1/models，再尝试 /api/tags
    tried = []
    for path in ["/models", "/v1/models"]:
        url = base + path
        tried.append(url)
        try:
            r = req_lib.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # OpenAI 格式: {"data": [{"id": "..."}]}
                if "data" in data:
                    ids = [m["id"] for m in data["data"] if "id" in m]
                    return {"models": sorted(ids)}
                # Ollama /api/tags 格式: {"models": [{"name": "..."}]}
                if "models" in data:
                    ids = [m.get("name", m.get("id", "")) for m in data["models"]]
                    return {"models": sorted(filter(None, ids))}
        except Exception:
            pass

    # Ollama 专属路径
    if req.type == "local":
        ollama_base = base.replace("/v1", "")
        try:
            r = req_lib.get(f"{ollama_base}/api/tags", timeout=10)
            if r.status_code == 200:
                data = r.json()
                ids = [m.get("name", "") for m in data.get("models", [])]
                return {"models": sorted(filter(None, ids))}
        except Exception:
            pass

    raise HTTPException(
        status_code=502,
        detail=f"{ZH.S_bf380ba31c}{tried}"
    )

_BENCH_EXCLUDE = [
    "vl", "vision", "image", "omni", "qvq",
    "audio", "tts", "asr", "speech", "livetranslate",
    "-mt-", "-mt", "mt-",
    "realtime", "gui", "z-image", "wan2",
    "character", "deep-search", "deep-research",
    "longcontext", "distill",
    "1.8b-", "0.5b-", "0.6b-", "1.7b-", "1.5b-instruct",
]

_BENCH_ADDRESS = "[Wang, Li] Peking Univ, Sch Phys, Beijing 100871, Peoples R China"
_BENCH_SYSTEM  = (
    "You are a geographic address parser. Extract location information and "
    "return ONLY a JSON: {\"Country/Region\":\"...\",\"City1\":\"...\",\"Organization\":\"...\",\"City2\":\"...\"}."
)
_BENCH_USER = f"Parse: {_BENCH_ADDRESS}\nReturn JSON:"

def _bench_should_exclude(model_id: str) -> bool:
    low = model_id.lower()
    return any(kw in low for kw in _BENCH_EXCLUDE)

def _bench_one_model(base: str, headers: dict, model_id: str,
                     timeout_s: float = 4.0) -> dict:
    """对单个模型发起测试请求，返回测速结果"""
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": _BENCH_SYSTEM},
            {"role": "user",   "content": _BENCH_USER},
        ],
        "temperature": 0,
        "max_tokens": 100,
        "stream": False,
    }
    t0 = time_module.perf_counter()
    try:
        r = req_lib.post(
            f"{base}/chat/completions",
            json=payload, headers=headers, timeout=timeout_s,
        )
        elapsed = round(time_module.perf_counter() - t0, 3)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        # 验证是否返回了有效 JSON
        m = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        valid = bool(m)
        return {"model": model_id, "elapsed": elapsed,
                "pass": valid, "error": None}
    except Exception as e:
        elapsed = round(time_module.perf_counter() - t0, 3)
        return {"model": model_id, "elapsed": elapsed,
                "pass": False, "error": str(e)[:80]}

@router.post("/api/models/benchmark")
def benchmark_models(req: BenchmarkRequest):
    """
    1. Fetch the model list
    2. Filter out non-chat models
    3. Test each model concurrently (send a real C1 parse request)
    4. Return models that pass (<= timeout), sorted by response time ascending
    """
    import concurrent.futures

    # ── 获取模型列表 ──────────────────────────
    list_req = ListModelsRequest(
        type=req.type, provider=req.provider,
        api_key=req.api_key, base_url=req.base_url,
    )
    try:
        list_resp = list_models(list_req)
        all_models: List[str] = list_resp["models"]
    except HTTPException as e:
        raise e

    # ── 过滤非对话类 ──────────────────────────
    candidates = [m for m in all_models if not _bench_should_exclude(m)]

    if not candidates:
        return {"passed": [], "failed": [], "total_tested": 0}

    tmp_cfg = AIConfig(type=req.type, provider=req.provider,
                       api_key=req.api_key, base_url=req.base_url)
    base    = _resolve_base_url(tmp_cfg)
    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"

    # Anthropic 走 Messages API，单独处理。
    # Anthropic 响应时间普遍较长，不做严格限时判定，只要能返回有效 JSON 即视为通过。
    if req.provider == "Anthropic":
        results = []
        for model_id in candidates:
            t0 = time_module.perf_counter()
            try:
                content = _anthropic_chat(base, req.api_key, model_id,
                                          _BENCH_SYSTEM, _BENCH_USER,
                                          max(req.timeout, 20.0), max_tokens=120)
                elapsed = round(time_module.perf_counter() - t0, 3)
                valid = bool(re.search(r'\{[^{}]*\}', content, re.DOTALL))
                results.append({"model": model_id, "elapsed": elapsed, "pass": valid, "error": None})
            except Exception as e:
                elapsed = round(time_module.perf_counter() - t0, 3)
                results.append({"model": model_id, "elapsed": elapsed, "pass": False, "error": str(e)[:80]})
        passed = sorted([r for r in results if r["pass"]], key=lambda x: x["elapsed"])
        failed = [r for r in results if not r["pass"]]
        return {"passed": passed, "failed": failed,
                "total_tested": len(candidates), "timeout": req.timeout}

    # Gemini 走自己的接口，单独处理
    if req.provider == "Gemini":
        # Gemini 用固定端点测试，复用 ai_parse_c1 逻辑
        results = []
        for model_id in candidates:
            t0 = time_module.perf_counter()
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models"
                    f"/{model_id}:generateContent?key={req.api_key}"
                )
                body = {"contents": [{"parts": [{"text": f"{_BENCH_SYSTEM}\n\n{_BENCH_USER}"}]}]}
                r = req_lib.post(url, json=body, timeout=req.timeout + 1)
                elapsed = round(time_module.perf_counter() - t0, 3)
                r.raise_for_status()
                content = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                valid = bool(re.search(r'\{[^{}]*\}', content, re.DOTALL))
                results.append({"model": model_id, "elapsed": elapsed, "pass": valid, "error": None})
            except Exception as e:
                elapsed = round(time_module.perf_counter() - t0, 3)
                results.append({"model": model_id, "elapsed": elapsed, "pass": False, "error": str(e)[:80]})
    else:
        # ── 并发测试 ──────────────────────────
        with concurrent.futures.ThreadPoolExecutor(max_workers=req.max_workers) as exe:
            futs = {
                exe.submit(_bench_one_model, base, headers, m, req.timeout + 1): m
                for m in candidates
            }
            results = [f.result() for f in concurrent.futures.as_completed(futs)]

    # ── 分类 & 排序 ───────────────────────────
    passed = sorted(
        [r for r in results if r["pass"] and r["elapsed"] <= req.timeout],
        key=lambda x: x["elapsed"],
    )
    failed = [r for r in results if not (r["pass"] and r["elapsed"] <= req.timeout)]

    return {
        "passed": passed,
        "failed": failed,
        "total_tested": len(candidates),
        "timeout": req.timeout,
    }

