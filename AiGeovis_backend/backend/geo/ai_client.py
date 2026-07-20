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

from core.schemas import AIConfig
from core.utils import parse_ai_json
from geo.prompts import _tier_system_prompt, _tier_user_prompt, _tier_parse_json
from geo.address import _sanitize_parse_result, _parse_result_issues, _tier_result_issues, _c3_result_issues
from geo.country import _normalize_country
from geo.prompts import _tier_parse_json, _tier_system_prompt, _tier_user_prompt

def _resolve_base_url(cfg: AIConfig) -> str:
    """根据 provider 解析 base_url"""
    if cfg.base_url.strip():
        return cfg.base_url.strip().rstrip("/")
    defaults = {
        "OpenAI":      "https://api.openai.com/v1",
        "DeepSeek":    "https://api.deepseek.com/v1",
        "SiliconFlow": "https://api.siliconflow.cn/v1",
        "Aliyun":      "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "Qwen":        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "Anthropic":   "https://api.anthropic.com",
        "Custom":      "",
    }
    if cfg.type == "local":
        return "http://localhost:11434/v1"
    return defaults.get(cfg.provider, "https://api.openai.com/v1")

def _anthropic_headers(api_key: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

def _anthropic_chat(base: str, api_key: str, model: str,
                    system_prompt: str, user_prompt: str,
                    timeout: float, max_tokens: int = 200) -> str:
    """调用 Anthropic Messages API，返回文本内容。"""
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    r = req_lib.post(f"{base}/v1/messages", json=body,
                     headers=_anthropic_headers(api_key), timeout=timeout)
    r.raise_for_status()
    blocks = r.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")

def ai_parse_c1(c1: str, cfg: AIConfig, timeout: float = 2.0, field: str = "C1") -> Dict:
    """
    调用单个 AI 模型解析一条 C1/C3 地址，同时返回经纬度坐标。
    field="C3" 时使用机构优先的 prompt，并触发后续机构级地理编码。
    timeout：每次请求的超时秒数，默认 2s，超时直接抛出异常。
    """
    if field == "C3":
        system_prompt = (
            "You are an expert at parsing academic institution names from the WoS C3 field.\n\n"
            "IMPORTANT: The input is a SINGLE institution affiliation string that has been "
            "concatenated from multiple lines. Spaces may separate what were originally separate lines.\n\n"
            "Your task is to extract these fields from the single institution string:\n"
            "- Country/Region: The country or region (e.g. 'United States', 'China', 'Germany')\n"
            "- Organization: The MAIN institution name. Ignore departments, labs, divisions.\n"
            "  Key patterns:\n"
            "  * 'University of X' -> 'University of X' (the FULL name)\n"
            "  * 'X University' -> 'X University'\n"
            "  * 'X Institute of Technology' -> 'X Institute of Technology'\n"
            "  * 'X University of Science & Technology' -> 'X University of Science & Technology'\n"
            "  * 'University System of Ohio' -> 'University System of Ohio' (this IS a system)\n"
            "  * 'Ohio State University' -> 'Ohio State University' (NOT 'University System of Ohio')\n"
            "  * 'M. S. Ramaiah University of Applied Sciences' -> 'M. S. Ramaiah University of Applied Sciences'\n"
            "  * 'Institute for Healthcare Improvement' -> 'Institute for Healthcare Improvement'\n"
            "- City1: The city where this institution is primarily located\n"
            "- lat: Latitude of the main campus as decimal\n"
            "- lng: Longitude of the main campus as decimal\n"
            "- City2: set to empty string for C3\n\n"
            "Return ONLY JSON: {\"Country/Region\":\"...\",\"Organization\":\"...\",\"City1\":\"...\",\"City2\":\"\",\"lat\":0.0,\"lng\":0.0}"
        )
        user_prompt = (
            f"Extract the MAIN institution (ignore departments/sub-units):\n{c1}\n\n"
            'Return ONLY JSON: {"Country/Region":"...","Organization":"...","City1":"...","City2":"","lat":0.0,"lng":0.0}'
        )
    else:
        system_prompt = (
            "You are a geographic address parser. Extract location information from the given address "
            "and return a JSON object with these exact fields:\n"
            "- Country/Region: The country or region name in English\n"
            "- Organization: The institution/organization name (ONLY the main institution, before the first comma)\n"
            "- City1: The city name only (no postal code or street)\n"
            "- City2: City with postal code and detailed address info (no country name)\n"
            "- lat: Latitude of the city/location as a decimal number (e.g. 39.9042)\n"
            "- lng: Longitude of the city/location as a decimal number (e.g. 116.4074)\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )
        user_prompt = (
            f"Parse this address:\n{c1}\n\n"
            'Return JSON: {"Country/Region":"...","Organization":"...","City1":"...","City2":"...","lat":0.0,"lng":0.0}'
        )

    headers = {"Content-Type": "application/json"}

    if cfg.type == "official" and cfg.provider == "Gemini":
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{cfg.model}:generateContent?key={cfg.api_key}"
        )
        body = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
        r = req_lib.post(url, json=body, timeout=timeout)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return parse_ai_json(text)

    if cfg.type == "official" and cfg.provider == "Anthropic":
        base = _resolve_base_url(cfg)
        text = _anthropic_chat(base, cfg.api_key, cfg.model,
                               system_prompt, user_prompt, timeout, max_tokens=200)
        return parse_ai_json(text)

    # OpenAI-compatible（官方 / 本地 Ollama）
    base = _resolve_base_url(cfg)
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 200,
    }
    r = req_lib.post(f"{base}/chat/completions", json=body,
                     headers=headers, timeout=timeout)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return parse_ai_json(text)

def ai_parse_tier(c1: str, tier: str, cfg: AIConfig, timeout: float = 2.0) -> Dict:
    """
    调用单个 AI 模型按层级解析一条地址（国家/城市/机构独立解析）。
    tier: "country" | "city" | "org"
    """
    system_prompt = _tier_system_prompt(tier)
    user_prompt_fn = _tier_user_prompt(tier)
    user_prompt = user_prompt_fn(c1)

    headers = {"Content-Type": "application/json"}

    if cfg.type == "official" and cfg.provider == "Gemini":
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{cfg.model}:generateContent?key={cfg.api_key}"
        )
        body = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
        r = req_lib.post(url, json=body, timeout=timeout)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _tier_parse_json(tier, text)

    if cfg.type == "official" and cfg.provider == "Anthropic":
        base = _resolve_base_url(cfg)
        text = _anthropic_chat(base, cfg.api_key, cfg.model,
                               system_prompt, user_prompt, timeout, max_tokens=150)
        return _tier_parse_json(tier, text)

    base = _resolve_base_url(cfg)
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 150,
    }
    r = req_lib.post(f"{base}/chat/completions", json=body,
                     headers=headers, timeout=timeout)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    return _tier_parse_json(tier, text)

