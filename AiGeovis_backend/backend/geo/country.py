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
    # 中国变体（主权国家主体）
    "p.r. china": "China",
    "p.r.china": "China",
    "pr china": "China",
    "peoples r china": "China",
    "people's republic of china": "China",
    "prc": "China",
    "china, mainland": "China",
    "mainland china": "China",
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
}

# 中国台湾 / 香港 / 澳门：表述以中国外交部/联合国用语为准；国家层计数不单独统计。
# 台湾：Taiwan, Province of China（中国台湾省）
# 港澳：Hong Kong / Macao (China)；Macao 为联合国英文拼写，兼容 Macau。
_CHINA_REGION_CANONICAL = {
    "taiwan": "Taiwan, Province of China",
    "hong kong": "Hong Kong (China)",
    "macao": "Macao (China)",
    "macau": "Macao (China)",
}

# 别名 → 规范基名（taiwan / hong kong / macao）
_CHINA_REGION_ALIASES = {
    "taiwan": "taiwan",
    "taiwan, china": "taiwan",
    "taiwan china": "taiwan",
    "taiwan(china)": "taiwan",
    "taiwan (china)": "taiwan",
    "chinese taipei": "taiwan",
    "taiwan province of china": "taiwan",
    "taiwan, province of china": "taiwan",
    "taiwan, province of china (china)": "taiwan",
    "china taiwan": "taiwan",
    "中国台湾": "taiwan",
    "中国台湾省": "taiwan",
    "台湾": "taiwan",
    "台湾省": "taiwan",
    "roc": "taiwan",
    "republic of china": "taiwan",
    "hong kong": "hong kong",
    "hong kong, china": "hong kong",
    "hong kong china": "hong kong",
    "hong kong(china)": "hong kong",
    "hong kong (china)": "hong kong",
    "hong kong sar": "hong kong",
    "hong kong special administrative region": "hong kong",
    "hong kong special administrative region of china": "hong kong",
    "hk": "hong kong",
    "hksar": "hong kong",
    "macao": "macao",
    "macau": "macao",
    "macao, china": "macao",
    "macau, china": "macao",
    "macao china": "macao",
    "macau china": "macao",
    "macao(china)": "macao",
    "macau(china)": "macao",
    "macao (china)": "macao",
    "macau (china)": "macao",
    "macao sar": "macao",
    "macau sar": "macao",
    "macao special administrative region": "macao",
    "macau special administrative region": "macao",
    "macao special administrative region of china": "macao",
    "macau special administrative region of china": "macao",
}

# 兼容旧代码引用
CHINA_REGIONS = {"taiwan", "hong kong", "macau", "macao"}

_CHINA_SUFFIX_RE = re.compile(r"\s*\(\s*china\s*\)\s*$", re.IGNORECASE)
_CHINA_COMMA_RE = re.compile(r"\s*,\s*china\s*$", re.IGNORECASE)


def _china_region_key(name: str) -> Optional[str]:
    """若属于中国台湾/香港/澳门，返回基名 taiwan|hong kong|macao；否则 None。"""
    if not name:
        return None
    key = re.sub(r"\s+", " ", str(name).strip().lower().rstrip("."))
    key = key.replace("（", "(").replace("）", ")")
    if key in _CHINA_REGION_ALIASES:
        return _CHINA_REGION_ALIASES[key]

    # Taiwan(China) / Taiwan , China 等松散写法
    bare = _CHINA_SUFFIX_RE.sub("", key).strip()
    bare = _CHINA_COMMA_RE.sub("", bare).strip()
    bare = re.sub(r"\s+", " ", bare)
    if bare in _CHINA_REGION_ALIASES:
        return _CHINA_REGION_ALIASES[bare]
    if bare in ("taiwan", "hong kong", "macao", "macau"):
        return "macao" if bare == "macau" else bare
    return None


def is_china_region_entity(name: str) -> bool:
    """是否为中国台湾/香港/澳门（国家层计数与国家共现中不单独统计）。"""
    return _china_region_key(name) is not None


def canonical_china_region_name(name: str) -> Optional[str]:
    """返回规范表述，如 Taiwan, Province of China；非此类地区返回 None。"""
    base = _china_region_key(name)
    if not base:
        return None
    return _CHINA_REGION_CANONICAL[base]


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
COUNTRY_COORDS.setdefault("taiwan (china)", (25.03, 121.57))
COUNTRY_COORDS.setdefault("taiwan, province of china", (25.03, 121.57))
COUNTRY_COORDS.setdefault("hong kong (china)", (22.32, 114.17))
COUNTRY_COORDS.setdefault("macao (china)", (22.20, 113.55))
COUNTRY_COORDS.setdefault("macau (china)", (22.20, 113.55))


def _lookup_country_coords(name: str) -> Optional[Tuple[float, float]]:
    """按国家名（已归一化）查询内置坐标表；兼容台湾省及 (China) 后缀形式。"""
    if not name:
        return None
    key = name.strip().lower()
    if key in COUNTRY_COORDS:
        return COUNTRY_COORDS[key]
    key2 = _CHINA_SUFFIX_RE.sub("", key).strip()
    if key2 and key2 in COUNTRY_COORDS:
        return COUNTRY_COORDS[key2]
    base = _china_region_key(name)
    if base and base in COUNTRY_COORDS:
        return COUNTRY_COORDS[base]
    return None


def _normalize_country(country: str) -> str:
    """
    标准化国家/地区名称。

    中国台湾省：Taiwan, Province of China（外交部/联合国用语）；
    香港、澳门：Hong Kong (China) / Macao (China)；
    国家层频次与共现统计另行排除这些实体，见 is_china_region_entity。
    """
    if not country:
        return country
    raw = country.strip().rstrip(".")
    if not raw:
        return country

    canon = canonical_china_region_name(raw)
    if canon:
        return canon

    key = re.sub(r"\s+", " ", raw.lower())
    if key in COUNTRY_NORMALIZE_MAP:
        return COUNTRY_NORMALIZE_MAP[key]

    return raw
