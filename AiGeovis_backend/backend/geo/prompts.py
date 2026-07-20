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

from geo.country import _normalize_country

def _tier_system_prompt(tier: str) -> str:
    if tier == "country":
        return (
            "You are a geographic address parser. Extract ONLY the country/region from the address "
            "and return a JSON object with these exact fields:\n"
            "- Country: The country or region name in English (e.g. China, United States, Germany)\n"
            "- lat: Latitude of the COUNTRY CENTER as a decimal number (e.g. 35.8617 for China)\n"
            "- lng: Longitude of the COUNTRY CENTER as a decimal number (e.g. 104.1954 for China)\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )
    elif tier == "city":
        return (
            "You are a geographic address parser. Extract ONLY the city from the address "
            "and return a JSON object with these exact fields:\n"
            "- City: The city name in English only (no country, no postal code, no street)\n"
            "- lat: Latitude of the CITY CENTER as a decimal number (e.g. 39.9042 for Beijing)\n"
            "- lng: Longitude of the CITY CENTER as a decimal number (e.g. 116.4074 for Beijing)\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )
    else:  # org
        return (
            "You are a geographic address parser. Extract ONLY the institution/organization name "
            "from the address and return a JSON object with these exact fields:\n"
            "- Organization: The main institution/organization name (ONLY the main institution, "
            "before the first comma if present, e.g. 'Chinese Academy of Sciences')\n"
            "- lat: Latitude of the institution location as a decimal number (city-level precision is fine)\n"
            "- lng: Longitude of the institution location as a decimal number\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )

def _tier_user_prompt(tier: str) -> callable:
    """返回生成 user_prompt 的闭包"""
    def make_prompt(c1: str) -> str:
        if tier == "country":
            return (
                f"Parse this address:\n{c1}\n\n"
                'Return JSON: {"Country":"...","lat":0.0,"lng":0.0}'
            )
        elif tier == "city":
            return (
                f"Parse this address:\n{c1}\n\n"
                'Return JSON: {"City":"...","lat":0.0,"lng":0.0}'
            )
        else:
            return (
                f"Parse this address:\n{c1}\n\n"
                'Return JSON: {"Organization":"...","lat":0.0,"lng":0.0}'
            )
    return make_prompt

def _tier_parse_json(tier: str, text: str) -> Dict:
    """根据层级解析 AI 返回的 JSON，返回规范化结果"""
    defaults = {
        "Country": "", "City": "", "Organization": "",
        "lat": None, "lng": None,
    }
    try:
        m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if m:
            obj = json.loads(m.group(0))
            defaults.update(obj)
            for k in ("lat", "lng"):
                v = defaults[k]
                try:
                    defaults[k] = float(v) if v not in (None, "", "null") else None
                except (TypeError, ValueError):
                    defaults[k] = None
            if tier == "country" and defaults.get("Country"):
                defaults["Country"] = _normalize_country(defaults["Country"])
    except Exception:
        pass
    return defaults

