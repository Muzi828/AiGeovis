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
from collections import Counter
from itertools import combinations
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

from core.reexport import pull
import geo.address as _geo_address
import geo.country as _geo_country
import geo.reference_cache as _geo_reference_cache
pull(_geo_address, globals())
pull(_geo_country, globals())
pull(_geo_reference_cache, globals())

from core.sessions import sessions
from geo.address import _field_cols, _field_parsed_df_key, _split_address_cell, _split_c3_field, _tier_cols, _tier_parsed_df_key
from geo.country import _normalize_country, is_china_region_entity
from geo.reference_cache import _tier_rule_parse

def _make_entity_id(
    tier: str,
    entity_name: str,
    country_name: Optional[str] = None,
) -> str:
    """
    生成实体的唯一标识。
    - tier=country : 标准化国家名；中国台湾/香港/澳门不进入国家层统计（返回空）
    - tier=city   : 直接返回城市名
    - tier=org    : 直接返回机构名
    """
    if tier == "country":
        name = _normalize_country(entity_name)
        if not name or is_china_region_entity(name):
            return ""
        return name
    return entity_name.strip()

def _tier_address_entities_by_paper(
    sess: Dict, field: str, tier: str
) -> pd.DataFrame:
    """按【文献 × 地址】重建 tier 解析实体表（保留原始文献索引）。

    通过“原始 df 按序拆分地址 + 与展开后的解析结果按位置对齐”恢复每条地址所属文献，
    返回带 MultiIndex(paper_idx, addr_idx) 的 DataFrame，列含 name/country/lat/lng/field。
    名称/国家/坐标一律 AI 优先、规则兜底，供 stats 与共现矩阵共用，保证口径一致。
    无数据时返回空 DataFrame。
    """
    df_key = _tier_parsed_df_key(field, tier)
    if df_key not in sess:
        return pd.DataFrame()

    df = sess[df_key]
    cols = _tier_cols(field, tier)
    name_col = cols["name"]
    lat_col = cols["lat"]
    lng_col = cols["lng"]

    country_col = _tier_cols(field, "country")["name"]

    if name_col not in df.columns:
        return pd.DataFrame()

    original_df = sess.get("df")
    if original_df is None or field not in original_df.columns:
        return pd.DataFrame()

    original_df = original_df.copy().reset_index(drop=True)
    parsed_rows = df.reset_index(drop=True)

    split_fn: Callable[[Any], List[str]] = _split_c3_field if field == "C3" else _split_address_cell

    rows: List[Dict[str, Any]] = []
    index_tuples: List[Tuple[Any, int]] = []
    parsed_pos = 0
    for paper_idx, original_row in original_df.iterrows():
        raw_value = original_row.get(field, "")
        addresses = split_fn(raw_value)
        for addr_idx, address in enumerate(addresses):
            if parsed_pos >= len(parsed_rows):
                break

            row = parsed_rows.iloc[parsed_pos]
            parsed_pos += 1
            addr_text = str(address).strip()
            if not addr_text:
                continue

            parsed_name = row.get(name_col)
            parsed_country = row.get(country_col) if country_col in row.index else None
            parsed_lat = row.get(lat_col)
            parsed_lng = row.get(lng_col)

            entity_name = None
            entity_country = None
            entity_lat = parsed_lat
            entity_lng = parsed_lng

            # ── 统一策略：AI 优先，规则兜底 ──────────────────
            # 名称、国家、坐标全部优先用批量上传时 AI 解析的结果；
            # 仅在该字段为空时才降级使用规则提取（避免两遍解析结果不一致）。
            if tier == "country":
                result = _tier_rule_parse("country", addr_text)
                # 名称：AI 优先，规则兜底
                entity_name = parsed_name or result.get("Country")
                entity_country = entity_name
                # 坐标：AI 优先，规则兜底
                if entity_lat is None or pd.isna(entity_lat) or entity_lng is None or pd.isna(entity_lng):
                    entity_lat = result.get("lat")
                    entity_lng = result.get("lng")
            elif tier in ("city", "org"):
                tier_result = _tier_rule_parse(tier, addr_text)
                country_result = _tier_rule_parse("country", addr_text)
                # 名称：AI 优先，规则兜底
                entity_name = parsed_name or tier_result.get("City" if tier == "city" else "Organization")
                # 国家：AI 优先，规则兜底
                entity_country = parsed_country or country_result.get("Country")
                # 坐标：AI 优先，规则兜底
                if entity_lat is None or pd.isna(entity_lat) or entity_lng is None or pd.isna(entity_lng):
                    entity_lat = tier_result.get("lat")
                    entity_lng = tier_result.get("lng")
            else:
                entity_name = parsed_name
                entity_country = parsed_country

            rows.append({
                name_col: entity_name,
                country_col: entity_country,
                lat_col: entity_lat,
                lng_col: entity_lng,
                field: addr_text,
            })
            index_tuples.append((paper_idx, addr_idx))

    if not rows:
        return pd.DataFrame()

    working = pd.DataFrame(rows)
    working.index = pd.MultiIndex.from_tuples(index_tuples, names=["paper_idx", "addr_idx"])
    return working

def _aggregate_paper_entities(
    sess: Dict, field: str, tier: str
) -> Tuple[Dict[int, Dict], Dict[str, Dict]]:
    """
    将地址级 tier 解析结果聚合为文献级实体集合。

    tier=city/org 时，实体的唯一标识直接使用名称本身。

    返回
    ───
    paper_entities: Dict[原文献index, {
        "entities": list[str],  # 去重后的实体ID列表
        "paper_idx": int,
    }]
    entity_coords: Dict[实体ID, {"lat": float, "lng": float}]
    """
    working = _tier_address_entities_by_paper(sess, field, tier)
    if working.empty:
        return {}, {}

    cols = _tier_cols(field, tier)
    name_col = cols["name"]
    lat_col = cols["lat"]
    lng_col = cols["lng"]
    country_col = _tier_cols(field, "country")["name"]

    # ── 1. 文献级实体去重集合 ──────────────────────
    paper_entities: Dict[int, Dict] = {}
    for orig_idx, group in working.groupby(level=0):
        normalized = []
        seen = set()
        for _, entity_row in group.iterrows():
            entity_name = entity_row.get(name_col)
            if pd.isna(entity_name):
                continue
            entity_name = str(entity_name).strip()
            if not entity_name:
                continue

            raw_country = entity_row.get(country_col)
            if pd.isna(raw_country) or not str(raw_country).strip():
                raw_country = None
            else:
                raw_country = str(raw_country).strip()

            eid = _make_entity_id(tier, entity_name, raw_country)
            if eid and eid not in seen:
                normalized.append(eid)
                seen.add(eid)

        paper_entities[orig_idx] = {
            "entities": normalized,
            "paper_idx": orig_idx,
        }

    # ── 2. 每个实体的代表坐标 ───────────────────────
    entity_coords: Dict[str, Dict] = {}
    for _, row in working.iterrows():
        entity_name = row.get(name_col)
        if pd.isna(entity_name):
            continue
        entity_name = str(entity_name).strip()
        if not entity_name:
            continue

        raw_country = row.get(country_col)
        if pd.isna(raw_country) or not str(raw_country).strip():
            raw_country = None
        else:
            raw_country = str(raw_country).strip()

        eid = _make_entity_id(tier, entity_name, raw_country)
        if not eid or eid in entity_coords:
            continue

        lat_v = row.get(lat_col)
        lng_v = row.get(lng_col)
        if lat_v is not None and lng_v is not None and not pd.isna(lat_v) and not pd.isna(lng_v):
            entity_coords[eid] = {
                "lat": round(float(lat_v), 5),
                "lng": round(float(lng_v), 5),
            }

    return paper_entities, entity_coords

def _aggregate_unified_c3_entities(sess: Dict, tier: str) -> Tuple[Dict[int, Dict], Dict[str, Dict]]:
    """将 C3 统一解析结果按文献聚合为实体集合，供 entity-matrix 复用。"""
    df_key = _field_parsed_df_key("C3")
    df = sess.get(df_key)
    original_df = sess.get("df")
    if df is None or original_df is None or "C3" not in original_df.columns:
        return {}, {}

    cols = _field_cols("C3")
    required_cols = [cols["country"], cols["org"], cols["city1"], cols["lat"], cols["lng"]]
    if any(col not in df.columns for col in required_cols):
        return {}, {}

    original_df = original_df.copy().reset_index(drop=True)
    parsed_rows = df.reset_index(drop=True)

    rows: List[Dict[str, Any]] = []
    index_tuples: List[Tuple[Any, int]] = []
    parsed_pos = 0
    for paper_idx, original_row in original_df.iterrows():
        raw_value = original_row.get("C3", "")
        addresses = _split_c3_field(raw_value)
        for addr_idx, address in enumerate(addresses):
            if parsed_pos >= len(parsed_rows):
                break

            parsed_row = parsed_rows.iloc[parsed_pos]
            parsed_pos += 1
            addr_text = str(address).strip()
            if not addr_text:
                continue

            country_name = parsed_row.get(cols["country"])
            org_name = parsed_row.get(cols["org"])
            city_name = parsed_row.get(cols["city1"])
            lat_v = parsed_row.get(cols["lat"])
            lng_v = parsed_row.get(cols["lng"])

            if pd.isna(country_name) or not str(country_name).strip():
                country_name = None
            else:
                country_name = _normalize_country(str(country_name).strip())

            def choose_entity_name() -> Any:
                if tier == "country":
                    return country_name
                if tier == "city":
                    if pd.isna(city_name):
                        return None
                    city_text = str(city_name).strip()
                    return city_text or None
                if pd.isna(org_name):
                    return None
                org_text = str(org_name).strip()
                return org_text or None

            entity_name = choose_entity_name()
            if not entity_name:
                continue

            rows.append({
                "entity_name": entity_name,
                "country_name": country_name,
                "lat": lat_v,
                "lng": lng_v,
            })
            index_tuples.append((paper_idx, addr_idx))

    if not rows:
        return {}, {}

    working = pd.DataFrame(rows)
    working.index = pd.MultiIndex.from_tuples(index_tuples, names=["paper_idx", "addr_idx"])

    paper_entities: Dict[int, Dict] = {}
    for orig_idx, group in working.groupby(level=0):
        normalized: List[str] = []
        seen: set = set()
        for _, entity_row in group.iterrows():
            entity_name = str(entity_row.get("entity_name") or "").strip()
            if not entity_name:
                continue

            raw_country = entity_row.get("country_name")
            if pd.isna(raw_country) or not str(raw_country).strip():
                raw_country = None
            else:
                raw_country = str(raw_country).strip()

            eid = _make_entity_id(tier, entity_name, raw_country)
            if eid and eid not in seen:
                normalized.append(eid)
                seen.add(eid)

        paper_entities[orig_idx] = {
            "entities": normalized,
            "paper_idx": orig_idx,
        }

    entity_coords: Dict[str, Dict] = {}
    for _, row in working.iterrows():
        entity_name = str(row.get("entity_name") or "").strip()
        if not entity_name:
            continue

        raw_country = row.get("country_name")
        if pd.isna(raw_country) or not str(raw_country).strip():
            raw_country = None
        else:
            raw_country = str(raw_country).strip()

        eid = _make_entity_id(tier, entity_name, raw_country)
        if not eid or eid in entity_coords:
            continue

        lat_v = row.get("lat")
        lng_v = row.get("lng")
        if lat_v is not None and lng_v is not None and not pd.isna(lat_v) and not pd.isna(lng_v):
            entity_coords[eid] = {
                "lat": round(float(lat_v), 5),
                "lng": round(float(lng_v), 5),
            }

    return paper_entities, entity_coords

def _unified_addr_entities_by_paper(sess: Dict, field: str) -> pd.DataFrame:
    """将统一解析结果（C1/C3）按【文献 × 地址】重建实体表，保留原始文献索引。

    返回列：_country（规范化国家名）、_org、_city、_lat、_lng；索引为
    MultiIndex(paper_idx, addr_idx)。供 viz-data 做整体计数（每篇每实体去重）使用，
    口径与共现矩阵 / 分层统计保持一致。若解析结果缺失则返回空表。
    """
    df = sess.get(_field_parsed_df_key(field))
    original_df = sess.get("df")
    if df is None or original_df is None or field not in original_df.columns:
        return pd.DataFrame()

    cols = _field_cols(field)
    required = [cols["country"], cols["org"], cols["city1"], cols["lat"], cols["lng"]]
    if any(c not in df.columns for c in required):
        return pd.DataFrame()

    original_df = original_df.copy().reset_index(drop=True)
    parsed_rows = df.reset_index(drop=True)
    split_fn = _split_c3_field if field == "C3" else _split_address_cell

    rows: List[Dict[str, Any]] = []
    index_tuples: List[Tuple[Any, int]] = []
    pos = 0
    for paper_idx, orow in original_df.iterrows():
        addresses = split_fn(orow.get(field, ""))
        for addr_idx, address in enumerate(addresses):
            if pos >= len(parsed_rows):
                break
            prow = parsed_rows.iloc[pos]
            pos += 1
            if not str(address).strip():
                continue

            country = prow.get(cols["country"])
            if pd.isna(country) or not str(country).strip():
                country = ""
            else:
                country = _normalize_country(str(country).strip())
            org = prow.get(cols["org"])
            org = "" if pd.isna(org) else str(org).strip()
            city = prow.get(cols["city1"])
            city = "" if pd.isna(city) else str(city).strip()

            rows.append({
                "_country": country,
                "_org": org,
                "_city": city,
                "_lat": prow.get(cols["lat"]),
                "_lng": prow.get(cols["lng"]),
            })
            index_tuples.append((paper_idx, addr_idx))

    if not rows:
        return pd.DataFrame()

    working = pd.DataFrame(rows)
    working.index = pd.MultiIndex.from_tuples(index_tuples, names=["paper_idx", "addr_idx"])
    return working

def _build_entity_matrix(
    paper_entities: Dict[int, Dict],
    entity_coords: Dict[str, Dict],
    top_n: int = 50,
    threshold: int = 0,
) -> Dict:
    """
    基于文献级实体集合构建共现矩阵、节点列表和边列表。

    参数
    ───
    paper_entities : 文献索引 → 实体ID列表
    entity_coords : 实体ID → 坐标
    top_n        : 最多参与矩阵的实体数量
    threshold    : 最小共现次数，低于此值的边不返回
    """
    if not paper_entities:
        return {
            "entities": [],
            "matrix": [],
            "nodes": [],
            "edges": [],
            "total_papers": 0,
            "papers_with_entity": 0,
            "papers_without_entity": 0,
            "total_pairs": 0,
        }

    # ── 1. 统计各实体在文献级出现的频次 ────────────
    entity_freq: Counter = Counter()
    for info in paper_entities.values():
        for e in info["entities"]:
            entity_freq[e] += 1

    total_papers = len(paper_entities)
    papers_with_entity = sum(1 for info in paper_entities.values() if info["entities"])
    papers_without_entity = total_papers - papers_with_entity

    # ── 2. 取 top_n 实体 ────────────────────────
    top_entities = [e for e, _ in entity_freq.most_common(top_n)]
    idx_map = {e: i for i, e in enumerate(top_entities)}
    n = len(top_entities)

    # ── 3. 构建共现矩阵 ────────────────────────
    matrix = [[0] * n for _ in range(n)]
    for info in paper_entities.values():
        entities = [e for e in info["entities"] if e in idx_map]
        unique_entities = list(dict.fromkeys(entities))
        for a, b in combinations(unique_entities, 2):
            i, j = idx_map[a], idx_map[b]
            matrix[i][j] += 1
            matrix[j][i] += 1
        for e in unique_entities:
            i = idx_map[e]
            matrix[i][i] += 1

    # ── 4. 构建节点列表 ────────────────────────
    nodes = []
    for e in top_entities:
        nodes.append({
            "name":      e,
            "frequency": entity_freq[e],
            "lat":       entity_coords.get(e, {}).get("lat"),
            "lng":       entity_coords.get(e, {}).get("lng"),
        })

    # ── 5. 构建边列表（仅上三角）───────────────────
    edges = []
    total_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            weight = matrix[i][j]
            if weight > 0:
                total_pairs += weight
            if weight >= threshold:
                edges.append({
                    "source": top_entities[i],
                    "target": top_entities[j],
                    "weight": weight,
                })

    return {
        "entities":              top_entities,
        "matrix":                matrix,
        "nodes":                 nodes,
        "edges":                 edges,
        "total_papers":          total_papers,
        "papers_with_entity":    papers_with_entity,
        "papers_without_entity": papers_without_entity,
        "total_pairs":           total_pairs,
    }

