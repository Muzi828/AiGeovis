from __future__ import annotations

import json
import re
from typing import Dict, Optional, Tuple

from core.paths import BACKEND_DIR

# ── 国家/地区标准化映射 ──────────────────────────
COUNTRY_NORMALIZE_MAP = {
    # 美国变体
    "usa": "United States",
    "u.s.a.": "United States",
    "u.s.a": "United States",
    "us": "United States",
    "u.s.": "United States",
    "u.s": "United States",
    "united states of america": "United States",
    "america": "United States",
    # 英国变体
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "u.k": "United Kingdom",
    "england": "United Kingdom",
    "scotland": "United Kingdom",
    "wales": "United Kingdom",
    "northern ireland": "United Kingdom",
    "great britain": "United Kingdom",
    "britain": "United Kingdom",
    # 中国变体
    "p.r. china": "China",
    "p.r.china": "China",
    "pr china": "China",
    "peoples r china": "China",
    "people's republic of china": "China",
    "prc": "China",
    # 德国变体
    "germany": "Germany",
    "deutschland": "Germany",
    "fed rep ger": "Germany",
    # 韩国变体
    "south korea": "South Korea",
    "korea": "South Korea",
    "republic of korea": "South Korea",
    # 俄罗斯变体
    "russia": "Russia",
    "russian federation": "Russia",
    # 其他常见变体
    "uae": "United Arab Emirates",
    "roc": "Taiwan (China)",
}

# 需要添加 (China) 后缀的地区
CHINA_REGIONS = {"taiwan", "hong kong", "macau", "macao"}

# ── 内置国家坐标表（离线，规则通道用；与前端 country.json 同源，格式 [lng, lat]）──
_COUNTRY_COORDS_PATH = BACKEND_DIR / "country_coords.json"
COUNTRY_COORDS: Dict[str, Tuple[float, float]] = {}
try:
    with open(_COUNTRY_COORDS_PATH, encoding="utf-8") as _f:
        for _name, _lnglat in json.load(_f).items():
            COUNTRY_COORDS[_name.strip().lower()] = (float(_lnglat[1]), float(_lnglat[0]))
except Exception:
    pass
# 坐标表未覆盖的常见地区补充（lat, lng）
COUNTRY_COORDS.setdefault("taiwan", (25.03, 121.57))
COUNTRY_COORDS.setdefault("hong kong", (22.32, 114.17))
COUNTRY_COORDS.setdefault("macau", (22.20, 113.55))
COUNTRY_COORDS.setdefault("macao", (22.20, 113.55))


def _lookup_country_coords(name: str) -> Optional[Tuple[float, float]]:
    """按国家名（已归一化）查询内置坐标表；兼容 "Taiwan (China)" 等后缀形式。"""
    if not name:
        return None
    key = name.strip().lower()
    if key in COUNTRY_COORDS:
        return COUNTRY_COORDS[key]
    key2 = re.sub(r"\s*\(china\)$", "", key).strip()
    if key2 and key2 in COUNTRY_COORDS:
        return COUNTRY_COORDS[key2]
    return None


def _normalize_country(country: str) -> str:
    """标准化国家/地区名称。"""
    if not country:
        return country
    raw = country.strip()
    key = raw.lower()

    # 先检查映射表
    if key in COUNTRY_NORMALIZE_MAP:
        return COUNTRY_NORMALIZE_MAP[key]

    # 检查是否需要添加 (China) 后缀
    for region in CHINA_REGIONS:
        if key == region or key.startswith(region + " ") or key.startswith(region + ","):
            if "(china)" not in key:
                return f"{raw} (China)"
            return raw

    return raw

