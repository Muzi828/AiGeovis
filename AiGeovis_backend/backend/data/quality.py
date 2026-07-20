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

from typing import List
import pandas as pd

_QUALITY_FIELDS = [
    ("TC", "Times Cited"), ("AU", "Authors"), ("LA", "Language"),
    ("TI", "Title"), ("PY", "Publication Year"), ("SO", "Source"),
    ("NR", "Cited Reference Count"), ("DT", "Document Type"),
    ("WC", "WoS Categories"), ("C1", "Author Address"),
    ("CR", "Cited References"), ("RP", "Reprint Address"),
    ("AB", "Abstract"), ("DI", "DOI"), ("ID", "Keywords Plus"),
    ("DE", "Author Keywords"),
]

def _split_multi(series: pd.Series, sep: str = ";") -> pd.Series:
    """把分号分隔的多值字段展开为去重后的取值 Series。"""
    s = series.dropna().astype(str)
    s = s[s.str.strip() != ""]
    return s.str.split(sep).explode().str.strip().replace("", np.nan).dropna()

def _duplicate_groups(df: pd.DataFrame, method: str) -> List[List[int]]:
    """按 DOI 或 DOI+标题 生成重复组（每组为行号列表，长度 >= 2）。"""
    keys: List[str] = []
    di = df["DI"] if "DI" in df.columns else pd.Series([""] * len(df), index=df.index)
    ti = df["TI"] if "TI" in df.columns else pd.Series([""] * len(df), index=df.index)
    for i, (d, t) in enumerate(zip(di.fillna(""), ti.fillna(""))):
        d_norm = str(d).strip().lower()
        if method == "doi_ti":
            t_norm = str(t).strip().lower()
            key = f"{d_norm}|||{t_norm}" if (d_norm or t_norm) else f"_empty_{i}"
        else:
            key = d_norm if d_norm else f"_empty_{i}"  # 空 DOI 不参与去重
        keys.append(key)

    groups: Dict[str, List[int]] = {}
    for pos, key in enumerate(keys):
        groups.setdefault(key, []).append(pos)
    return [g for g in groups.values() if len(g) >= 2]

