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
from core.i18n import ZH, _tr, _tr_issues, _join_issues, _tier_label, _is_en
from core.schemas import AIConfig
from core.utils import parse_ai_json
from core.reexport import pull
import geo.address as _geo_address
import geo.prompts as _geo_prompts
import geo.ai_client as _geo_ai_client
import geo.geocoders as _geo_geocoders
import geo.reference_cache as _geo_reference_cache
import geo.country as _geo_country
pull(_geo_address, globals())
pull(_geo_prompts, globals())
pull(_geo_ai_client, globals())
pull(_geo_geocoders, globals())
pull(_geo_reference_cache, globals())
pull(_geo_country, globals())

from core.i18n import _join_issues, _tier_label, _tr
from core.sessions import parse_progress, sessions, stop_flags
from geo.address import _c3_result_issues, _explode_address_field, _field_cols, _field_parsed_df_key, _parse_result_issues, _sanitize_parse_result, _tier_cols, _tier_parsed_df_key, _tier_result_issues, rule_parse_c1
from geo.ai_client import _anthropic_chat, _resolve_base_url, ai_parse_c1, ai_parse_tier
from geo.country import _normalize_country
from geo.geocoders import _batch_nominatim_geocode
from geo.reference_cache import _affiliation_cache_get, _affiliation_parse_json, _affiliation_result_issues, _ref_match_tier, _tier_rule_parse

def _parse_single_subtype(
    sid: str, df_sub: pd.DataFrame, subtype: str,
    cfgs: List[AIConfig], model_labels: List[str],
    batch_size: int, prog: Dict, stop_ev: threading.Event,
    skip_cache: bool = False, lang: str = "zh",
):
    """
    解析单个子类型的 affiliation 数据（国家/机构/城市）。
    解析完成后直接写入 session 的对应 parsed DataFrame。
    """
    PARSE_TIMEOUT        = 2.0
    FINAL_PARSE_TIMEOUT  = 8.0
    MAX_IDLE_ROUND       = 3

    if subtype == "affiliation_country":
        name_col = "Country/Region"
    elif subtype == "affiliation_city":
        name_col = "City1"
    else:
        name_col = "Organization"

    name_vals = df_sub[name_col].dropna().astype(str).str.strip()
    name_vals = name_vals[name_vals != ""]
    unique_names = name_vals.unique().tolist()
    total = len(unique_names)
    num_models = len(cfgs)

    lbl = _tier_label(subtype, lang)
    prog["logs"].append(_tr(lang,
        f"[{lbl}{ZH.S_d237338231}{total}{ZH.S_77d386365b}{num_models}{ZH.S_03df0992fa}{PARSE_TIMEOUT}{ZH.S_3f5552e0f3}"
        + (ZH.S_c4c875f2d1 if skip_cache else ""),
        f"[{lbl}] Start | {total} unique names | {num_models} model(s) | timeout {PARSE_TIMEOUT}s/req"
        + (" | skip cache" if skip_cache else ""),
    ))

    if total == 0:
        sessions[sid][f"parsed_df_{subtype}"] = df_sub.copy()
        prog["status"] = "done"
        prog["progress"] = 100
        prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_1be16a5594}", f"[{lbl}] No names to parse"))
        return

    # ── 本地缓存预填充 ──
    cache: Dict[str, Dict] = {}
    cache_lock = threading.Lock()
    pending = list(unique_names)
    round_num = 0
    idle_rounds = 0
    attempted_models: Dict[str, set] = {}
    # 主轮各模型的尝试/成功次数，用于最终阶段挑选“成功率最高”的单一模型
    model_attempts: Dict[str, int] = {lbl: 0 for lbl in model_labels}
    model_success:  Dict[str, int] = {lbl: 0 for lbl in model_labels}

    # ── 本地缓存命中：直接从 pending 中剔除已缓存的名称 ──
    cached_hit = 0
    still_pending = []
    if skip_cache:
        still_pending = list(pending)
        prog["logs"].append(_tr(lang,
            ZH.S_3b67d66108,
            "  🗃 Skipped reference DB; re-parsing all with LLM"))
    else:
        for name in pending:
            cached = _affiliation_cache_get(name)
            if cached is not None:
                issues = _affiliation_result_issues(cached)
                if not issues:
                    cache[name] = cached
                    cached_hit += 1
                else:
                    still_pending.append(name)
            else:
                still_pending.append(name)
        prog["logs"].append(_tr(lang,
            f"{ZH.S_caad6cfd1d}{cached_hit}/{total}{ZH.S_098b266908}",
            f"  🗃 Reference DB hit {cached_hit}/{total}, skipping AI"))
    pending = still_pending
    if not pending:
        prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_3435494fd2}",
                                 f"[{lbl}] All cached, done instantly!"))

    def _build_prompt(name: str) -> Tuple[str, str]:
        system_prompt = (
            "You are a geographic name parser. Given a name, return its primary location "
            "coordinates as a JSON object with these two fields:\n"
            "- lat: decimal latitude (e.g. 39.9042 for Beijing)\n"
            "- lng: decimal longitude (e.g. 116.4074 for Beijing)\n\n"
            "Rules:\n"
            "- For countries: use the capital city coordinates.\n"
            "- For institutions: use the primary campus or headquarters coordinates.\n"
            "- For departments/embedded addresses: extract the city or institution location.\n"
            "Return ONLY the JSON object, no markdown, no explanation."
        )
        user_prompt = f"Parse this name:\n{name}\n\nReturn JSON: {{\"lat\":0.0,\"lng\":0.0}}"
        return system_prompt, user_prompt

    def process_one(cfg: AIConfig, label: str, name: str, timeout: float = PARSE_TIMEOUT) -> bool:
        try:
            attempted_models.setdefault(name, set()).add(label)
            model_attempts[label] = model_attempts.get(label, 0) + 1
            system_prompt, user_prompt = _build_prompt(name)
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
                result = _affiliation_parse_json(text)
            elif cfg.type == "official" and cfg.provider == "Anthropic":
                base = _resolve_base_url(cfg)
                text = _anthropic_chat(base, cfg.api_key, cfg.model,
                                       system_prompt, user_prompt, timeout, max_tokens=150)
                result = _affiliation_parse_json(text)
            else:
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
                result = _affiliation_parse_json(text)

            result["_src"] = "ai"
            result["_model"] = label

            issues = _affiliation_result_issues(result)
            if issues:
                preview = str(name)
                prog["logs"].append(_tr(lang,
                    f"  ⚠ [{label}{ZH.S_aeda4a320d}{preview} | {_join_issues(issues, 'zh', 2)}",
                    f"  ⚠ [{label}] incomplete: {preview} | {_join_issues(issues, 'en', 2)}"))
                return False

            # 仅写入当前会话内存；固定参考库只读，不回写磁盘
            with cache_lock:
                cache[name] = result
                model_success[label] = model_success.get(label, 0) + 1
            preview = str(name)
            prog["logs"].append(f"  ✓ [{label}] {preview}")
            return True

        except Exception as e:
            err = str(e)
            if "timeout" in err.lower() or "timed out" in err.lower():
                prog["logs"].append(_tr(lang, f"  ⏱ [{label}{ZH.S_e3fd360e5f}{name}",
                                        f"  ⏱ [{label}] timeout: {name}"))
            else:
                prog["logs"].append(_tr(lang, f"  ✗ [{label}{ZH.S_689581b610}{err}",
                                        f"  ✗ [{label}] error: {err}"))
            return False

    # ═══ 阶段 1：主轮轮询 ═══
    prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_d07a44409e}",
                            f"[{lbl}] Stage 1: multi-model fast parse"))

    while pending and not stop_ev.is_set():
        round_num += 1
        round_pending = list(pending)
        pending = []

        prog["logs"].append(_tr(lang, f"{ZH.S_2df8a1e714}{round_num}{ZH.S_3be5fe67b8}{len(round_pending)}{ZH.S_e14ca9c88d}",
                                f"  ── Round {round_num}: {len(round_pending)} names ──"))

        for batch_start in range(0, len(round_pending), batch_size):
            if stop_ev.is_set():
                break
            batch = round_pending[batch_start: batch_start + batch_size]

            assignments: List[List[str]] = [[] for _ in range(num_models)]
            for i, name in enumerate(batch):
                if name in cache:
                    continue
                tried = attempted_models.get(name, set())
                candidate_indexes = [
                    idx for idx, lbl in enumerate(model_labels)
                    if lbl not in tried
                ]
                if not candidate_indexes:
                    continue
                target_idx = candidate_indexes[(round_num + i) % len(candidate_indexes)]
                assignments[target_idx].append(name)

            threads = []
            failed_lists: List[List[str]] = []
            for idx, (cfg, label) in enumerate(zip(cfgs, model_labels)):
                if not assignments[idx]:
                    continue
                fl: List[str] = []
                failed_lists.append(fl)
                t = threading.Thread(
                    target=lambda cfg, lbl, tasks, out: [
                        process_one(cfg, lbl, n) or out.append(n) for n in tasks
                    ],
                    args=(cfg, label, assignments[idx], fl),
                    daemon=True,
                )
                threads.append(t)
                t.start()

            for t in threads:
                while t.is_alive():
                    if stop_ev.is_set():
                        break
                    t.join(timeout=0.3)

            for fl in failed_lists:
                pending.extend(fl)

            prog["progress"] = min(int(len(cache) / total * 90), 90)

        round_ok = len([n for n in round_pending if n in cache])
        prog["logs"].append(_tr(lang,
            f"{ZH.S_1a48e09bee}{round_num}{ZH.S_3b2e601f56}{round_ok}{ZH.S_3e4ff6c5ce}{len(pending)}{ZH.S_987e97f4d0}{len(cache)}/{total}",
            f"  Round {round_num} done: {round_ok} ok, {len(pending)} to retry, {len(cache)}/{total} total"))

        if round_ok == 0 and len(pending) > 0:
            idle_rounds += 1
            if idle_rounds >= MAX_IDLE_ROUND:
                pending = []
                break
        else:
            idle_rounds = 0

    # ═══ 阶段 2：最终修复 ═══
    prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_de44ab745e}", f"[{lbl}] Stage 2: final repair"))

    final_candidates = [
        name for name in unique_names
        if name not in cache or _affiliation_result_issues(cache.get(name, {}))
    ]

    ai_models = [
        (cfg, label) for cfg, label in zip(cfgs, model_labels)
        if cfg.type == "local" or bool(cfg.api_key)
    ]

    if not final_candidates:
        prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_d97d01f9b7}",
                                 f"[{lbl}] All names fully parsed"))
    elif not ai_models:
        prog["logs"].append(_tr(lang,
            f"[{lbl}] {len(final_candidates)}{ZH.S_2a2eeeba05}",
            f"[{lbl}] {len(final_candidates)} to repair, but no AI configured, skipped"))
    elif not stop_ev.is_set():
        # 只用主轮中“成功率最高”的单一模型做最终修复：避免 N 个名称 × 全部模型的巨大开销，
        # 成功率最高的模型往往也最准；用更长超时给它一次机会，仍失败即放弃该名称。
        def _rate(label: str) -> float:
            att = model_attempts.get(label, 0)
            return (model_success.get(label, 0) / att) if att > 0 else 0.0
        best_cfg, best_label = max(
            ai_models,
            key=lambda cl: (_rate(cl[1]), model_success.get(cl[1], 0)),
        )
        b_att = model_attempts.get(best_label, 0)
        b_suc = model_success.get(best_label, 0)
        prog["logs"].append(_tr(lang,
            f"[{lbl}{ZH.S_0bfed077e9}{len(final_candidates)}{ZH.S_need_fix}"
            f"{ZH.S_pick_best_model}{best_label}]"
            f"{ZH.S_paren_rate}{b_suc}/{b_att}{ZH.S_cn_comma}{_rate(best_label) * 100:.0f}{ZH.S_8b022af1f4}{FINAL_PARSE_TIMEOUT}{ZH.S_3f5552e0f3}",
            f"[{lbl}] Final: {len(final_candidates)} to repair, "
            f"using best model [{best_label}] "
            f"({b_suc}/{b_att}, {_rate(best_label) * 100:.0f}%), timeout {FINAL_PARSE_TIMEOUT}s/req"))
        repaired = 0
        for i, name in enumerate(final_candidates):
            if stop_ev.is_set():
                break
            cfg, label = best_cfg, best_label
            try:
                system_prompt, user_prompt = _build_prompt(name)
                headers = {"Content-Type": "application/json"}
                if cfg.type == "official" and cfg.provider == "Gemini":
                    url = (
                        f"https://generativelanguage.googleapis.com/v1beta/models"
                        f"/{cfg.model}:generateContent?key={cfg.api_key}"
                    )
                    body = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
                    r = req_lib.post(url, json=body, timeout=FINAL_PARSE_TIMEOUT)
                    r.raise_for_status()
                    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                    result = _affiliation_parse_json(text)
                elif cfg.type == "official" and cfg.provider == "Anthropic":
                    base = _resolve_base_url(cfg)
                    text = _anthropic_chat(base, cfg.api_key, cfg.model,
                                           system_prompt, user_prompt,
                                           FINAL_PARSE_TIMEOUT, max_tokens=150)
                    result = _affiliation_parse_json(text)
                else:
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
                                     headers=headers, timeout=FINAL_PARSE_TIMEOUT)
                    r.raise_for_status()
                    text = r.json()["choices"][0]["message"]["content"]
                    result = _affiliation_parse_json(text)

                result["_src"] = "final-ai"
                result["_model"] = f"final:{label}"

                preview = str(name)
                if not _affiliation_result_issues(result):
                    with cache_lock:
                        cache[name] = result
                    repaired += 1
                    prog["logs"].append(_tr(lang, f"{ZH.S_1304f43377}{label}]: {preview}",
                                            f"    ✓ Repaired [{label}]: {preview}"))
                else:
                    prog["logs"].append(_tr(lang, f"{ZH.S_5b1016bef8}{label}]: {preview}",
                                            f"    ✗ Still failing [{label}]: {preview}"))
            except Exception as e:
                preview = str(name)
                prog["logs"].append(_tr(lang, f"{ZH.S_de8b013ca7}{label}] {preview}: {str(e)}",
                                        f"    ✗ Final error [{label}] {preview}: {str(e)}"))

            prog["progress"] = min(90 + int(10 * (i + 1) / max(len(final_candidates), 1)), 99)

        still_broken = len([n for n in final_candidates if n not in cache])
        prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_e8e0063a99}{repaired}{ZH.S_5d2af7d2ae}{ZH.S_f059508497}{still_broken}{ZH.S_59d76cf338}",
                                 f"[{lbl}] Repaired {repaired}, {still_broken} still incomplete"))

    # ── 将解析结果回填到 df_sub 并写入 session ──
    lat_vals: Dict[Any, float]  = {}
    lng_vals: Dict[Any, float]  = {}
    src_vals: Dict[Any, str]    = {}
    model_vals_out: Dict[Any, str] = {}

    for idx, row in df_sub.iterrows():
        name = str(row.get(name_col, "")).strip()
        if name and name in cache:
            p = cache[name]
            lat_v = p.get("lat"); lng_v = p.get("lng")
            lat_vals[idx]   = float(lat_v) if lat_v is not None else np.nan
            lng_vals[idx]   = float(lng_v) if lng_v is not None else np.nan
            src_vals[idx]   = str(p.get("_src") or p.get("src") or "")
            model_vals_out[idx] = str(p.get("_model") or p.get("model") or "")
        elif name:
            src_vals[idx]       = "pending"
            model_vals_out[idx] = "need-other-model"

    for col, val_dict in [("ParseSrc", src_vals), ("ParseModel", model_vals_out)]:
        new_col = pd.Series(val_dict, dtype=object)
        df_sub[col] = new_col.reindex(df_sub.index, fill_value=np.nan)

    for col, val_dict in [("lat", lat_vals), ("lng", lng_vals)]:
        new_col = pd.Series(val_dict, dtype=float)
        df_sub[col] = new_col.reindex(df_sub.index, fill_value=np.nan)

    sessions[sid][f"parsed_df_{subtype}"] = df_sub.copy()

    success_count = len(cache)
    failed_count = total - success_count
    success_rate = round(success_count / total * 100, 2) if total > 0 else 0

    prog["report"] = {
        "total": total,
        "success": success_count,
        "failed": failed_count,
        "success_rate": success_rate,
    }

    if stop_ev.is_set():
        prog["status"] = "stopped"
        prog["progress"] = int(success_count / total * 100) if total > 0 else 0
        prog["logs"].append(_tr(lang,
            f"[{lbl}{ZH.S_3b5dabe8ba}{success_count}/{total}{ZH.S_bdc3ef7cc5}{success_rate}%",
            f"[{lbl}] ⏹ Stopped | {success_count}/{total} | success rate {success_rate}%"))
    else:
        prog["status"] = "done"
        prog["progress"] = 100
        prog["logs"].append(_tr(lang,
            f"[{lbl}{ZH.S_ada63452ab}{success_count}/{total}{ZH.S_bdc3ef7cc5}{success_rate}%",
            f"[{lbl}] ✅ Done! success {success_count}/{total} | success rate {success_rate}%"))

def _bg_parse_affiliation(sid: str, df: pd.DataFrame,
                           cfgs: List[AIConfig], batch_size: int,
                           skip_cache: bool = False, lang: str = "zh"):
    """
    后台任务：一次性解析所有三个子类型（国家/机构/城市）。
    每个子类型使用独立线程并发执行，解析完成后分别写入对应的 parsed DataFrame。
    """
    prog = parse_progress.get(sid)
    if not prog:
        return
    stop_ev = stop_flags.get(sid, threading.Event())

    model_labels = []
    for cfg in cfgs:
        label = cfg.name or cfg.model
        if cfg.type == "official" and cfg.provider not in ("Custom",):
            label = f"{cfg.provider}:{label}"
        model_labels.append(label)

    prog["logs"] = [_tr(lang,
        f"{ZH.S_2c25baff2d}{len(df)}{ZH.S_e09991d26d}{len(cfgs)}{ZH.S_44850b044b}",
        f"Starting affiliation parse | {len(df)} records | {len(cfgs)} model(s)")]
    if skip_cache:
        prog["logs"].append(_tr(lang, ZH.S_87d741df7a,
                                "Mode: skip reference DB, force LLM re-parse"))
    else:
        prog["logs"].append(_tr(lang, ZH.S_c284a8c31f,
                                "Mode: prefer reference DB (read-only)"))
    prog["logs"].append(_tr(lang, f"{ZH.S_4062627ab9}{', '.join(model_labels)}",
                            f"Models: {', '.join(model_labels)}"))

    subtypes = ["affiliation_country", "affiliation_org", "affiliation_city"]

    for subtype in subtypes:
        if stop_ev.is_set():
            break
        df_sub = df[df["_affiliation_type"] == subtype].copy()
        if df_sub.empty:
            sessions[sid][f"parsed_df_{subtype}"] = pd.DataFrame()
            _lbl0 = _tier_label(subtype, lang)
            prog["tiers"][subtype] = {
                "status": "done", "progress": 100,
                "logs": [_tr(lang, f"[{_lbl0}{ZH.S_dfdac5a4d6}", f"[{_lbl0}] No data, skipped")]
            }
            continue

        # 在当前线程解析此子类型（多子类型已通过循环串行，同步解析足够）
        tier_prog = prog["tiers"][subtype]
        _parse_single_subtype(
            sid, df_sub, subtype, cfgs, model_labels, batch_size, tier_prog, stop_ev,
            skip_cache=skip_cache, lang=lang,
        )

    # 计算总体进度
    total_progress = 0
    for st in subtypes:
        p = prog["tiers"].get(st, {})
        total_progress += p.get("progress", 0)
    prog["progress"] = total_progress // len(subtypes)

    all_done = all(
        prog["tiers"].get(st, {}).get("status") == "done" for st in subtypes
    )
    any_stopped = any(
        prog["tiers"].get(st, {}).get("status") == "stopped" for st in subtypes
    )

    total_all = sum(prog["tiers"].get(st, {}).get("report", {}).get("total", 0) for st in subtypes)
    success_all = sum(prog["tiers"].get(st, {}).get("report", {}).get("success", 0) for st in subtypes)
    failed_all = sum(prog["tiers"].get(st, {}).get("report", {}).get("failed", 0) for st in subtypes)
    success_rate_all = round(success_all / total_all * 100, 2) if total_all > 0 else 0

    prog["report"] = {
        "total": total_all,
        "success": success_all,
        "failed": failed_all,
        "success_rate": success_rate_all,
        "by_tier": {
            st: prog["tiers"].get(st, {}).get("report", {})
            for st in subtypes
        }
    }

    if any_stopped:
        prog["status"] = "stopped"
    elif all_done:
        prog["status"] = "done"
        prog["logs"].append(_tr(lang,
            f"{ZH.S_20c302ef11}{success_rate_all}%",
            f"✅ All done | country/org/city completed | success rate {success_rate_all}%"))

def _bg_parse_tier(sid: str, df: pd.DataFrame, cfgs: List[AIConfig],
                   batch_size: int, field: str, tier: str,
                   skip_cache: bool = False, lang: str = "zh"):
    """分层解析后台任务（与 _bg_parse_c1 逻辑类似，但只解析单一层级）

    增量匹配：country / org 两层先查固定参考库（大小写不敏感），命中即用库内
    坐标、跳过大模型；未命中的地址才进入后续多模型解析。city 不在库中，直接解析。
    skip_cache=True 时忽略参考库，全部交由大模型（全量解析）。
    """
    PARSE_TIMEOUT       = 2.0
    FINAL_PARSE_TIMEOUT = 8.0
    MAX_IDLE_ROUND      = 3

    tier_key  = f"{sid}_{tier}"
    prog      = parse_progress[sid]["tiers"][tier]
    stop_ev   = stop_flags.get(tier_key, threading.Event())
    use_ai    = any(bool(c.api_key) or c.type == "local" for c in cfgs)
    cols      = _tier_cols(field, tier)

    try:
        original_rows = len(df)
        df = _explode_address_field(df, field)
        exploded_rows = len(df)
        if exploded_rows > original_rows:
            prog["logs"].append(_tr(lang,
                f"{ZH.S_f25692c9cb}{field}{ZH.S_99da6f1e75}{original_rows}{ZH.S_948623584a}{ZH.S_c3efb6223e}{exploded_rows}{ZH.S_59d76cf338}",
                f"Field {field} expanded: {original_rows} rows → {exploded_rows} address rows"))

        c1_vals   = df[field].dropna().astype(str).str.strip()
        c1_vals   = c1_vals[c1_vals != ""]
        unique_c1 = c1_vals.unique().tolist()
        total      = len(unique_c1)
        num_models = len(cfgs)

        model_labels = []
        for cfg in cfgs:
            label = cfg.name or cfg.model
            if cfg.type == "official" and cfg.provider not in ("Custom",):
                label = f"{cfg.provider}:{label}"
            model_labels.append(label)

        lbl = _tier_label(tier, lang)
        prog["logs"].append(_tr(lang,
            f"{ZH.S_d5a69aa0c9}{lbl}{ZH.S_fb72d76935}{field}{ZH.S_fac6485384}{total}{ZH.S_b5f24efa6c}{num_models}{ZH.S_03df0992fa}{PARSE_TIMEOUT}{ZH.S_3f5552e0f3}",
            f"Tier parse [{lbl}] | field: {field} | {total} unique addresses | {num_models} model(s) | timeout {PARSE_TIMEOUT}s/req"))

        if total == 0:
            sessions[sid][_tier_parsed_df_key(field, tier)] = df
            prog["status"] = "done"
            prog["progress"] = 100
            prog["logs"].append(_tr(lang,
                f"{lbl}{ZH.S_ea0eaf03af}{field}{ZH.S_fe0c993578}",
                f"{lbl} parse: no addresses to parse in field {field}"))
            return

        cache:      Dict[str, Dict] = {}
        cache_lock  = threading.Lock()
        pending     = list(unique_c1)
        round_num   = 0
        idle_rounds = 0
        attempted_models: Dict[str, set] = {}
        unresolved_after_all_models: set = set()
        # 主轮各模型的尝试/成功次数，用于最终阶段挑选“成功率最高”的单一模型
        model_attempts: Dict[str, int] = {lbl: 0 for lbl in model_labels}
        model_success:  Dict[str, int] = {lbl: 0 for lbl in model_labels}

        name_key = {"country": "Country", "city": "City", "org": "Organization"}[tier]

        # ── 固定参考库增量匹配（仅 country / org；city 不在库中）──
        # 从原始地址中抽取国家/机构 token，去库里做大小写不敏感精确匹配；
        # 命中即用库内坐标并跳过大模型，未命中的地址继续走后续解析流程。
        if tier in ("country", "org"):
            if skip_cache:
                prog["logs"].append(_tr(lang,
                    ZH.S_2fdf3b2995,
                    "  🗃 Skipped reference DB; parsing all with LLM"))
            else:
                ref_hit = 0
                still_pending = []
                for c1_val in pending:
                    m = _ref_match_tier(tier, c1_val)
                    if m is not None:
                        name_val, lat_v, lng_v, model_v = m
                        result = {
                            name_key: name_val,
                            "lat": lat_v,
                            "lng": lng_v,
                            "_src": "db",
                            "_model": model_v,
                        }
                        if not _tier_result_issues(tier, result):
                            cache[c1_val] = result
                            ref_hit += 1
                            continue
                    still_pending.append(c1_val)
                pending = still_pending
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_caad6cfd1d}{ref_hit}/{total}{ZH.S_098b266908}",
                    f"  🗃 Reference DB hit {ref_hit}/{total}, skipping AI"))
                if not pending:
                    prog["logs"].append(_tr(lang, f"[{lbl}{ZH.S_38040c8dfb}",
                                             f"[{lbl}] All matched in reference DB, done instantly!"))

        def process_one(cfg: AIConfig, label: str, c1_val: str,
                        timeout: float = PARSE_TIMEOUT) -> bool:
            try:
                attempted_models.setdefault(c1_val, set()).add(label)
                model_attempts[label] = model_attempts.get(label, 0) + 1
                if use_ai and (cfg.api_key or cfg.type == "local"):
                    result = ai_parse_tier(c1_val, tier, cfg, timeout=timeout)
                    result["_src"] = "ai"
                else:
                    result = _tier_rule_parse(tier, c1_val)
                    result["_src"] = "rule"
                result["_model"] = label

                issues = _tier_result_issues(tier, result)
                if issues:
                    preview = str(c1_val)
                    prog["logs"].append(_tr(lang,
                        f"⚠ [{label}] [{lbl}{ZH.S_aeda4a320d}{preview} | {_join_issues(issues, 'zh', 2)}",
                        f"⚠ [{label}] [{lbl}] incomplete: {preview} | {_join_issues(issues, 'en', 2)}"))
                    return False

                with cache_lock:
                    cache[c1_val] = result
                    model_success[label] = model_success.get(label, 0) + 1
                preview = str(c1_val)
                prog["logs"].append(f"✓ [{label}] [{lbl}] {preview}")
                return True
            except Exception as e:
                err = str(e)
                if "timeout" in err.lower() or "timed out" in err.lower():
                    prog["logs"].append(_tr(lang, f"⏱ [{label}{ZH.S_e3fd360e5f}{c1_val}",
                                            f"⏱ [{label}] timeout: {c1_val}"))
                else:
                    prog["logs"].append(_tr(lang, f"✗ [{label}{ZH.S_689581b610}{err}",
                                            f"✗ [{label}] error: {err}"))
                return False

        def model_worker(cfg: AIConfig, label: str,
                         tasks: List[str], failed_out: List[str]):
            for c1_val in tasks:
                if stop_ev.is_set():
                    failed_out.append(c1_val)
                    return
                if not process_one(cfg, label, c1_val):
                    failed_out.append(c1_val)

        # 阶段 1：多模型轮询
        prog["logs"].append(_tr(lang, f"═══ [{lbl}{ZH.S_ea9e410d45}",
                                f"═══ [{lbl}] Stage 1: multi-model parse ═══"))
        while pending and not stop_ev.is_set():
            round_num += 1
            round_pending = list(pending)
            pending = []

            prog["logs"].append(_tr(lang, f"{ZH.S_353d620c12}{round_num}{ZH.S_3be5fe67b8}{len(round_pending)}{ZH.S_81a686f1af}",
                                    f"── Round {round_num}: {len(round_pending)} addresses ──"))

            for batch_start in range(0, len(round_pending), batch_size):
                if stop_ev.is_set():
                    break
                batch = round_pending[batch_start: batch_start + batch_size]

                assignments: List[List[str]] = [[] for _ in range(num_models)]
                exhausted: List[str] = []
                for i, val in enumerate(batch):
                    if val in cache:
                        continue
                    tried = attempted_models.get(val, set())
                    candidate_indexes = [
                        idx for idx, lbl in enumerate(model_labels)
                        if lbl not in tried
                    ]
                    if not candidate_indexes:
                        exhausted.append(val)
                        continue
                    target_idx = candidate_indexes[(round_num + i) % len(candidate_indexes)]
                    assignments[target_idx].append(val)

                threads = []
                failed_lists: List[List[str]] = []
                for idx, (cfg, label) in enumerate(zip(cfgs, model_labels)):
                    if not assignments[idx]:
                        continue
                    fl: List[str] = []
                    failed_lists.append(fl)
                    t = threading.Thread(
                        target=model_worker,
                        args=(cfg, label, assignments[idx], fl),
                        daemon=True,
                    )
                    threads.append(t)
                    t.start()

                for t in threads:
                    while t.is_alive():
                        if stop_ev.is_set():
                            break
                        t.join(timeout=0.3)

                for fl in failed_lists:
                    pending.extend(fl)

                if exhausted:
                    prog["logs"].append(_tr(lang,
                        f"   {len(exhausted)}{ZH.S_7d55c093d9}",
                        f"   {len(exhausted)} addresses tried all models, entering final stage"))
                    unresolved_after_all_models.update(exhausted)

                finished_count = len(cache) + len(unresolved_after_all_models)
                prog["progress"] = min(int(finished_count / total * 90), 90)

            round_ok = len([v for v in round_pending if v in cache])
            round_unresolved = len([v for v in round_pending if v in unresolved_after_all_models])
            prog["logs"].append(_tr(lang,
                f"{ZH.S_2cfdfc96a7}{round_num}{ZH.S_3b2e601f56}{round_ok}{ZH.S_d079564cea}{round_unresolved}{ZH.S_cn_comma}"
                f"{ZH.S_fail_retry}{len(pending)}{ZH.S_987e97f4d0}{len(cache)}/{total}",
                f"   Round {round_num} done: {round_ok} ok, {round_unresolved} pending, "
                f"{len(pending)} to retry, {len(cache)}/{total} total"))
            if round_ok == 0 and round_unresolved == 0:
                idle_rounds += 1
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_31d4879f0d}{idle_rounds}/{MAX_IDLE_ROUND}{ZH.S_cn_comma_close}"
                    + (ZH.S_3c0bb5c541 if idle_rounds < MAX_IDLE_ROUND else ZH.S_a8ed9d2016),
                    f"   No progress this round ({idle_rounds}/{MAX_IDLE_ROUND}), "
                    + ("retrying..." if idle_rounds < MAX_IDLE_ROUND else "giving up rest, entering final stage")))
                if idle_rounds >= MAX_IDLE_ROUND:
                    unresolved_after_all_models.update(pending)
                    pending = []
                    break
            else:
                idle_rounds = 0

        if pending:
            unresolved_after_all_models.update(pending)
            pending = []

        # 阶段 2：最终修复
        prog["logs"].append(_tr(lang, f"═══ [{lbl}{ZH.S_c8c22776b8}",
                                f"═══ [{lbl}] Stage 2: final repair ═══"))
        final_candidates = []
        for addr in unique_c1:
            if addr in cache:
                issues = _tier_result_issues(tier, cache[addr])
                if issues:
                    del cache[addr]
                    final_candidates.append(addr)
            else:
                final_candidates.append(addr)

        ai_models = [
            (cfg, label) for cfg, label in zip(cfgs, model_labels)
            if cfg.type == "local" or bool(cfg.api_key)
        ]

        if not final_candidates:
            prog["logs"].append(_tr(lang, ZH.S_26245c87e1,
                                    "Final stage: all addresses fully parsed, no repair needed"))
        elif not ai_models:
            unresolved_after_all_models.update(final_candidates)
            prog["logs"].append(_tr(lang,
                f"{ZH.S_50550ece75}{len(final_candidates)}{ZH.S_0875f836a0}",
                f"Final stage: {len(final_candidates)} addresses to repair, but no usable AI model, skipped"))
        elif not stop_ev.is_set():
            # 只用主轮中“成功率最高”的单一模型做最终修复：避免 N 个地址 × 全部模型的巨大开销，
            # 成功率最高的模型往往也最准；用更长超时给它一次机会，仍失败即放弃该地址。
            def _rate(label: str) -> float:
                att = model_attempts.get(label, 0)
                return (model_success.get(label, 0) / att) if att > 0 else 0.0
            best_cfg, best_label = max(
                ai_models,
                key=lambda cl: (_rate(cl[1]), model_success.get(cl[1], 0)),
            )
            b_att = model_attempts.get(best_label, 0)
            b_suc = model_success.get(best_label, 0)
            prog["logs"].append(_tr(lang,
                f"{ZH.S_f4878dd08a}{len(final_candidates)}{ZH.S_need_fix_addr}"
                f"{ZH.S_pick_best_model}{best_label}]"
                f"{ZH.S_paren_rate}{b_suc}/{b_att}{ZH.S_cn_comma}{_rate(best_label) * 100:.0f}{ZH.S_8b022af1f4}{FINAL_PARSE_TIMEOUT}{ZH.S_3f5552e0f3}",
                f"Final stage: {len(final_candidates)} addresses to repair, "
                f"using best model [{best_label}] "
                f"({b_suc}/{b_att}, {_rate(best_label) * 100:.0f}%), timeout {FINAL_PARSE_TIMEOUT}s/req"))
            repaired = 0
            for c1_val in final_candidates:
                if stop_ev.is_set():
                    unresolved_after_all_models.add(c1_val)
                    continue
                preview = str(c1_val)
                solved = False
                try:
                    result = ai_parse_tier(c1_val, tier, best_cfg, timeout=FINAL_PARSE_TIMEOUT)
                    result["_src"] = "final-ai"
                    result["_model"] = f"final:{best_label}"
                    if not _tier_result_issues(tier, result):
                        with cache_lock:
                            cache[c1_val] = result
                        unresolved_after_all_models.discard(c1_val)
                        repaired += 1
                        solved = True
                        prog["logs"].append(_tr(lang, f"{ZH.S_970f0e9c98}{best_label}]: {preview}",
                                                f"   ✓ Repaired [{best_label}]: {preview}"))
                    else:
                        prog["logs"].append(_tr(lang, f"{ZH.S_dd490b1053}{best_label}]: {preview}",
                                                f"   ✗ Still failing [{best_label}]: {preview}"))
                except Exception as e:
                    prog["logs"].append(_tr(lang, f"{ZH.S_18f7bd26e3}{best_label}] {preview}: {str(e)}",
                                            f"   ✗ Final error [{best_label}] {preview}: {str(e)}"))
                if not solved:
                    unresolved_after_all_models.add(c1_val)
                prog["progress"] = min(90 + int(10 * (final_candidates.index(c1_val) + 1) / max(len(final_candidates), 1)), 99)

            still_broken = len([a for a in final_candidates if a not in cache])
            prog["logs"].append(_tr(lang, f"{ZH.S_08e7b77ea3}{repaired}{ZH.S_5d2af7d2ae}{ZH.S_f059508497}{still_broken}{ZH.S_5d2af7d2ae}",
                                    f"Final stage done: repaired {repaired}, {still_broken} still incomplete"))

        # ── 收集所有写入值，用列级批量赋值避免 pandas 2.x 逐格严格类型检查 ──
        name_col  = cols["name"]
        lat_col   = cols["lat"]
        lng_col   = cols["lng"]
        src_col   = cols["src"]
        model_col = cols["model"]

        # 初始化目标列为 NaN（object 类型）
        for col in [name_col, lat_col, lng_col, src_col, model_col]:
            if col not in df.columns:
                df[col] = np.nan

        # 收集结果
        name_vals: Dict[Any, str]  = {}
        lat_vals:  Dict[Any, float] = {}
        lng_vals:  Dict[Any, float] = {}
        src_vals:  Dict[Any, str]  = {}
        model_vals:Dict[Any, str]  = {}

        for idx, row in df.iterrows():
            raw = row.get(field, "")
            v = str(raw).strip() if pd.notna(raw) else ""
            if v and v in cache:
                p = cache[v]
                lat_v = p.get("lat")
                lng_v = p.get("lng")
                name_vals[idx]   = str(p.get(name_key, "") or "")
                lat_vals[idx]    = float(lat_v) if lat_v is not None else np.nan
                lng_vals[idx]    = float(lng_v) if lng_v is not None else np.nan
                src_vals[idx]    = str(p.get("_src", "") or "")
                model_vals[idx]  = str(p.get("_model", "") or "")
            elif v:
                src_vals[idx]   = "pending"
                model_vals[idx] = "need-other-model"

        # 列级一次性赋值
        for col, val_dict in [(name_col, name_vals), (src_col, src_vals),
                               (model_col, model_vals)]:
            new_col = pd.Series(val_dict, dtype=object)
            df[col] = new_col.reindex(df.index, fill_value=np.nan)

        for col, val_dict in [(lat_col, lat_vals), (lng_col, lng_vals)]:
            new_col = pd.Series(val_dict, dtype=float)
            df[col] = new_col.reindex(df.index, fill_value=np.nan)

        sessions[sid][_tier_parsed_df_key(field, tier)] = df

        if stop_ev.is_set():
            prog["status"]   = "stopped"
            prog["progress"] = int(len(cache) / total * 100)
            prog["logs"].append(_tr(lang, f"{ZH.S_6c308de674}{len(cache)}/{total}{ZH.S_ad29083184}",
                                    f"⏹ Stopped | done {len(cache)}/{total} addresses"))
        else:
            prog["status"]   = "done"
            prog["progress"] = 100
            prog["logs"].append(_tr(lang,
                f"✅ {lbl}{ZH.S_d8ac209b72}{round_num}{ZH.S_b173832080}{len(cache)}/{total}{ZH.S_5c96b9c187}{len(df)}{ZH.S_02b44ef924}",
                f"✅ {lbl} parse done! {round_num} rounds | success {len(cache)}/{total} | wrote {len(df)} address rows"))

        # 生成解析结果统计
        prog["report"] = {
            "total": total,
            "success": len(cache),
            "failed": len(unresolved_after_all_models),
            "success_rate": round(len(cache) / total * 100, 2) if total > 0 else 0,
        }

    except Exception as e:
        prog["status"] = "error"
        prog["logs"].append(_tr(lang, f"{ZH.S_7449367fa2}{e}", f"Error: {e}"))
        traceback.print_exc()

def _bg_parse_c1(sid: str, df: pd.DataFrame, cfgs: List[AIConfig],
                 batch_size: int, field: str = "C1", skip_cache: bool = False,
                 lang: str = "zh"):
    """
    后台任务：多模型并行解析指定字段（C1 或 C3）地址
    ─────────────────────────────────────────────
    流程：
      阶段 0 — 参考库增量匹配（仅 C3）：C3 是机构名，先按 机构名→坐标 查固定参考库，
               命中即用库内坐标、跳过大模型；skip_cache=True 时忽略库（全量重算）。
      阶段 1 — 主轮：多模型轮询分配，2s 超时，失败换模型重试
      阶段 2 — 最终修复：收集所有仍不完整/0坐标的地址，选主轮成功率最高的单一模型重试
    ─────────────────────────────────────────────
    """
    PARSE_TIMEOUT       = 2.0   # 阶段 1 单次 AI 请求超时（秒）
    FINAL_PARSE_TIMEOUT = 8.0   # 阶段 2 最终修复，给大模型更长时间
    MAX_IDLE_ROUND      = 3     # 连续无进展最多重试轮数

    prog    = parse_progress[sid]
    stop_ev = stop_flags.get(sid, threading.Event())
    use_ai  = any(bool(c.api_key) or c.type == "local" for c in cfgs)
    cols    = _field_cols(field)

    try:
        # ── 展开地址行 ──────────────────────────────
        original_rows = len(df)
        df = _explode_address_field(df, field)
        exploded_rows = len(df)
        if exploded_rows > original_rows:
            prog["logs"].append(_tr(lang,
                f"{ZH.S_f25692c9cb}{field}{ZH.S_99da6f1e75}{original_rows}{ZH.S_948623584a}{ZH.S_c3efb6223e}{exploded_rows}",
                f"Field {field} expanded: {original_rows} rows → {exploded_rows} address rows"))

        # ── 唯一地址值 ─────────────────────────────
        c1_vals   = df[field].dropna().astype(str).str.strip()
        c1_vals   = c1_vals[c1_vals != ""]
        unique_c1 = c1_vals.unique().tolist()
        total      = len(unique_c1)
        num_models = len(cfgs)

        model_labels = []
        for cfg in cfgs:
            label = cfg.name or cfg.model
            if cfg.type == "official" and cfg.provider not in ("Custom",):
                label = f"{cfg.provider}:{label}"
            model_labels.append(label)

        prog["logs"].append(_tr(lang,
            f"{ZH.S_ab28765753}{field}{ZH.S_fac6485384}{total}{ZH.S_b5f24efa6c}{num_models}{ZH.S_03df0992fa}{PARSE_TIMEOUT}{ZH.S_3f5552e0f3}",
            f"Field: {field} | {total} unique addresses | {num_models} model(s) | timeout {PARSE_TIMEOUT}s/req"))
        prog["logs"].append(_tr(lang,
            f"{field}{ZH.S_112dd14360}{exploded_rows}{ZH.S_99b09fd190}{total}{ZH.S_8de362b496}",
            f"{field} split by semicolon and deduplicated: {exploded_rows} address rows → {total} unique addresses"))
        prog["logs"].append(_tr(lang, f"{ZH.S_4062627ab9}{', '.join(model_labels)}",
                                f"Models: {', '.join(model_labels)}"))

        if total == 0:
            sessions[sid][_field_parsed_df_key(field)] = df
            prog["status"] = "done"
            prog["progress"] = 100
            prog["logs"].append(_tr(lang, f"{ZH.S_f25692c9cb}{field}{ZH.S_fe0c993578}",
                                    f"Field {field} has no addresses to parse"))
            return

        # ── 本次运行的解析结果（纯内存，不做任何持久化/增量恢复）──────
        cache:      Dict[str, Dict] = {}
        cache_lock  = threading.Lock()

        pending     = list(unique_c1)   # 全量从零开始
        round_num   = 0
        idle_rounds = 0
        attempted_models: Dict[str, set] = {}
        unresolved_after_all_models: set = set()
        # 主轮各模型的尝试/成功次数，用于最终阶段挑选“成功率最高”的单一模型
        model_attempts: Dict[str, int] = {lbl: 0 for lbl in model_labels}
        model_success:  Dict[str, int] = {lbl: 0 for lbl in model_labels}

        # ── 阶段 0：C3 固定参考库增量匹配（机构名 → 坐标）──────────────
        # C3 字段本身就是机构名（无国家/城市），先按机构名去库里做大小写不敏感精确匹配，
        # 命中即用库内坐标、跳过大模型；未命中的才进入后续多模型解析。
        # skip_cache=True 时忽略参考库，全部交由大模型（全量重算）。
        if field == "C3":
            if skip_cache:
                prog["logs"].append(_tr(lang,
                    ZH.S_31c585a23a,
                    "🗃 Skipped reference DB; parsing all with LLM (full)"))
            else:
                ref_hit = 0
                still_pending = []
                for org_val in pending:
                    rec = _affiliation_cache_get(org_val)
                    if rec is not None:
                        result = {
                            "Country/Region": "",   # 机构本身不含国家
                            "Organization":   org_val,   # 显示沿用原始大小写
                            "City1":          "",
                            "City2":          "",
                            "lat":            rec.get("lat"),
                            "lng":            rec.get("lng"),
                            "_src":           "db",
                            "_model":         rec.get("_model", "wos-ref"),
                        }
                        if not _c3_result_issues(result):
                            cache[org_val] = result
                            ref_hit += 1
                            continue
                    still_pending.append(org_val)
                pending = still_pending
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_6f7f1b61f6}{ref_hit}/{total}{ZH.S_73f01561e4}",
                    f"🗃 Reference DB hit {ref_hit}/{total} orgs, skipping AI"))
                if not pending:
                    prog["logs"].append(_tr(lang, ZH.S_cbd5c22fa1,
                                             "C3: all matched in reference DB, done instantly!"))

        # ── 单地址处理函数（带超时）────────────────
        def process_one(cfg: AIConfig, label: str, c1_val: str,
                        timeout: float = PARSE_TIMEOUT) -> bool:
            """返回 True = 成功写入 cache，False = 需要重试/换模型"""
            try:
                attempted_models.setdefault(c1_val, set()).add(label)
                model_attempts[label] = model_attempts.get(label, 0) + 1
                if use_ai and (cfg.api_key or cfg.type == "local"):
                    result = ai_parse_c1(c1_val, cfg, timeout=timeout, field=field)
                    result["_src"] = "ai"
                else:
                    result = rule_parse_c1(c1_val)
                    result["_src"] = "rule"
                result["_model"] = label
                if result.get("Country/Region"):
                    result["Country/Region"] = _normalize_country(result["Country/Region"])
                result = _sanitize_parse_result(result)

                # C3：机构名一律沿用输入的 C3 原始机构名（WoS C3 本就是规范化机构名），
                # 不采用 AI 改写后的名称，否则同一机构在“库命中(原名)”与“AI(改写名)”之间
                # 会被拆成多个实体，导致频次统计偏低（如 CNRS 被拆分）。
                if field == "C3":
                    result["Organization"] = c1_val

                if field == "C3":
                    issues = _c3_result_issues(result)
                else:
                    issues = _parse_result_issues(result)

                if issues:
                    preview = str(c1_val)
                    prog["logs"].append(_tr(lang,
                        f"⚠ [{label}{ZH.S_aa048795c0}{preview} | {_join_issues(issues, 'zh', 3)}",
                        f"⚠ [{label}] incomplete, trying other model: {preview} | {_join_issues(issues, 'en', 3)}"))
                    return False

                with cache_lock:
                    cache[c1_val] = result
                    model_success[label] = model_success.get(label, 0) + 1
                preview = str(c1_val)
                prog["logs"].append(f"✓ [{label}] {preview}")
                return True
            except Exception as e:
                err = str(e)
                if "timeout" in err.lower() or "timed out" in err.lower():
                    prog["logs"].append(_tr(lang, f"⏱ [{label}{ZH.S_4d15d14051}{c1_val}",
                                            f"⏱ [{label}] timeout, skipped: {c1_val}"))
                else:
                    prog["logs"].append(_tr(lang, f"✗ [{label}{ZH.S_d1a8c34329}{err}): {c1_val}",
                                            f"✗ [{label}] skipped ({err}): {c1_val}"))
                return False

        # ── 单模型线程函数 ────────────────────────────
        def model_worker(cfg: AIConfig, label: str,
                         tasks: List[str], failed_out: List[str]):
            for c1_val in tasks:
                if stop_ev.is_set():
                    failed_out.append(c1_val)
                    return
                if not process_one(cfg, label, c1_val):
                    failed_out.append(c1_val)

        # ═══════════════════════════════════════════════
        # 阶段 1 — 主轮：多模型轮询分配
        # ═══════════════════════════════════════════════
        prog["logs"].append(_tr(lang, ZH.S_ee785b44db,
                                "═══ Stage 1: multi-model fast parse ═══"))
        while pending and not stop_ev.is_set():
            round_num += 1
            round_pending = list(pending)
            pending = []

            prog["logs"].append(_tr(lang,
                f"{ZH.S_353d620c12}{round_num}{ZH.S_3be5fe67b8}{len(round_pending)}{ZH.S_81a686f1af}",
                f"── Round {round_num}: {len(round_pending)} addresses ──"))

            for batch_start in range(0, len(round_pending), batch_size):
                if stop_ev.is_set():
                    break

                batch = round_pending[batch_start: batch_start + batch_size]

                assignments: List[List[str]] = [[] for _ in range(num_models)]
                exhausted: List[str] = []
                for i, val in enumerate(batch):
                    if val in cache:
                        continue
                    tried = attempted_models.get(val, set())
                    candidate_indexes = [
                        idx for idx, lbl in enumerate(model_labels)
                        if lbl not in tried
                    ]
                    if not candidate_indexes:
                        exhausted.append(val)
                        continue
                    target_idx = candidate_indexes[(round_num + i) % len(candidate_indexes)]
                    assignments[target_idx].append(val)

                threads = []
                failed_lists: List[List[str]] = []
                for idx, (cfg, label) in enumerate(zip(cfgs, model_labels)):
                    if not assignments[idx]:
                        continue
                    fl: List[str] = []
                    failed_lists.append(fl)
                    t = threading.Thread(
                        target=model_worker,
                        args=(cfg, label, assignments[idx], fl),
                        daemon=True,
                    )
                    threads.append(t)
                    t.start()

                for t in threads:
                    while t.is_alive():
                        if stop_ev.is_set():
                            break
                        t.join(timeout=0.3)

                for fl in failed_lists:
                    pending.extend(fl)

                if exhausted:
                    prog["logs"].append(_tr(lang,
                        f"   {len(exhausted)}{ZH.S_08150aba99}",
                        f"   {len(exhausted)} addresses tried all models but incomplete, entering final stage"))
                    unresolved_after_all_models.update(exhausted)

                finished_count = len(cache) + len(unresolved_after_all_models)
                prog["progress"] = min(int(finished_count / total * 90), 90)

            round_ok = len([v for v in round_pending if v in cache])
            round_unresolved = len([v for v in round_pending if v in unresolved_after_all_models])
            prog["logs"].append(_tr(lang,
                f"{ZH.S_2cfdfc96a7}{round_num}{ZH.S_3b2e601f56}{round_ok}{ZH.S_d079564cea}{round_unresolved}{ZH.S_cn_comma}"
                f"{ZH.S_fail_retry}{len(pending)}{ZH.S_987e97f4d0}{len(cache)}/{total}",
                f"   Round {round_num} done: {round_ok} ok, {round_unresolved} pending, "
                f"{len(pending)} to retry, {len(cache)}/{total} total"))

            if round_ok == 0 and round_unresolved == 0:
                idle_rounds += 1
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_31d4879f0d}{idle_rounds}/{MAX_IDLE_ROUND}{ZH.S_cn_comma_close}"
                    + (ZH.S_3c0bb5c541 if idle_rounds < MAX_IDLE_ROUND else ZH.S_a8ed9d2016),
                    f"   No progress this round ({idle_rounds}/{MAX_IDLE_ROUND}), "
                    + ("retrying..." if idle_rounds < MAX_IDLE_ROUND else "giving up rest, entering final stage")))
                if idle_rounds >= MAX_IDLE_ROUND:
                    unresolved_after_all_models.update(pending)
                    pending = []
                    break
            else:
                idle_rounds = 0

        # 主轮残余也归入最终阶段
        if pending:
            unresolved_after_all_models.update(pending)
            pending = []

        # ═══════════════════════════════════════════════
        # 阶段 2 — 最终修复：必须执行，收集所有不完整/0坐标地址
        # ═══════════════════════════════════════════════
        prog["logs"].append(_tr(lang, ZH.S_3394943a05,
                                "═══ Stage 2: final repair (incomplete/zero-coord) ═══"))

        # 不依赖 unresolved 集合，而是真正遍历全部唯一地址，重新检查 cache 中的结果
        _issues_fn = _c3_result_issues if field == "C3" else _parse_result_issues

        final_candidates = []
        for addr in unique_c1:
            if addr in cache:
                issues = _issues_fn(cache[addr])
                if issues:
                    # 从 cache 中移除有问题的结果，强制重新解析
                    del cache[addr]
                    final_candidates.append(addr)
            else:
                final_candidates.append(addr)

        ai_models = [
            (cfg, label) for cfg, label in zip(cfgs, model_labels)
            if cfg.type == "local" or bool(cfg.api_key)
        ]

        if not final_candidates:
            prog["logs"].append(_tr(lang, ZH.S_26245c87e1,
                                    "Final stage: all addresses fully parsed, no repair needed"))
        elif not ai_models:
            unresolved_after_all_models.update(final_candidates)
            prog["logs"].append(_tr(lang,
                f"{ZH.S_50550ece75}{len(final_candidates)}{ZH.S_0875f836a0}",
                f"Final stage: {len(final_candidates)} addresses to repair, but no usable AI model, skipped"))
        elif stop_ev.is_set():
            unresolved_after_all_models.update(final_candidates)
            prog["logs"].append(_tr(lang, ZH.S_b0c5ae0680,
                                    "Final stage: stopped by user, skipped"))
        else:
            # 只用主轮中“成功率最高”的单一模型做最终修复：避免 N 个地址 × 全部模型的巨大开销，
            # 成功率最高的模型往往也最准；用更长超时给它一次机会，仍失败即放弃该地址。
            def _rate(label: str) -> float:
                att = model_attempts.get(label, 0)
                return (model_success.get(label, 0) / att) if att > 0 else 0.0
            best_cfg, best_label = max(
                ai_models,
                key=lambda cl: (_rate(cl[1]), model_success.get(cl[1], 0)),
            )
            b_att = model_attempts.get(best_label, 0)
            b_suc = model_success.get(best_label, 0)
            prog["logs"].append(_tr(lang,
                f"{ZH.S_f4878dd08a}{len(final_candidates)}{ZH.S_need_fix_addr}"
                f"{ZH.S_pick_best_model}{best_label}]"
                f"{ZH.S_paren_rate}{b_suc}/{b_att}{ZH.S_cn_comma}{_rate(best_label) * 100:.0f}{ZH.S_8b022af1f4}{FINAL_PARSE_TIMEOUT}{ZH.S_3f5552e0f3}",
                f"Final stage: {len(final_candidates)} addresses to repair, "
                f"using best model [{best_label}] "
                f"({b_suc}/{b_att}, {_rate(best_label) * 100:.0f}%), timeout {FINAL_PARSE_TIMEOUT}s/req"))
            repaired = 0
            for c1_val in final_candidates:
                if stop_ev.is_set():
                    unresolved_after_all_models.add(c1_val)
                    continue
                preview = str(c1_val)
                solved = False
                try:
                    result = ai_parse_c1(c1_val, best_cfg, timeout=FINAL_PARSE_TIMEOUT, field=field)
                    result["_src"] = "final-ai"
                    result["_model"] = f"final:{best_label}"
                    if result.get("Country/Region"):
                        result["Country/Region"] = _normalize_country(result["Country/Region"])
                    result = _sanitize_parse_result(result)
                    # C3：机构名沿用输入原名，保证频次统计一致（同上）
                    if field == "C3":
                        result["Organization"] = c1_val

                    issues = _c3_result_issues(result) if field == "C3" else _issues_fn(result)
                    if not issues:
                        with cache_lock:
                            cache[c1_val] = result
                        unresolved_after_all_models.discard(c1_val)
                        repaired += 1
                        solved = True
                        prog["logs"].append(_tr(lang, f"{ZH.S_c7a844ef42}{best_label}]: {preview}",
                                                f"   ✓ Repaired [{best_label}]: {preview}"))
                    else:
                        prog["logs"].append(_tr(lang,
                            f"{ZH.S_74a9dc6291}{best_label}]: {preview} | {_join_issues(issues, 'zh', 3)}",
                            f"   Final stage failed [{best_label}]: {preview} | {_join_issues(issues, 'en', 3)}"))
                except Exception as e:
                    prog["logs"].append(_tr(lang,
                        f"{ZH.S_48589c5729}{best_label}] {preview}: {str(e)}",
                        f"   Final stage error [{best_label}] {preview}: {str(e)}"))

                if not solved:
                    unresolved_after_all_models.add(c1_val)

                prog["progress"] = min(90 + int(10 * (unique_c1.index(c1_val) + 1) / len(final_candidates)), 99)

            still_broken = len([a for a in final_candidates if a not in cache])
            prog["logs"].append(_tr(lang,
                f"{ZH.S_08e7b77ea3}{repaired}{ZH.S_5d2af7d2ae}{ZH.S_f059508497}{still_broken}{ZH.S_5d2af7d2ae}",
                f"Final stage done: repaired {repaired}, {still_broken} still incomplete"))

        # ═══════════════════════════════════════════════
        # 阶段 3 — C3 批量 Nominatim 补救（仅 C3）
        #   在所有 AI 解析完成后，对仍有经纬度问题的记录批量查询 Nominatim
        # ═══════════════════════════════════════════════
        if field == "C3":
            nominatim_items: List[Tuple[str, str]] = []
            for addr in unique_c1:
                if addr not in cache:
                    continue
                r = cache[addr]
                lat_v = r.get("lat")
                lng_v = r.get("lng")
                if lat_v is None or lng_v is None or (abs(float(lat_v) if lat_v is not None else 0) < 1e-9
                    and abs(float(lng_v) if lng_v is not None else 0) < 1e-9):
                    org = r.get("Organization", "").strip()
                    country = r.get("Country/Region", "").strip()
                    if org and country:
                        nominatim_items.append((org, country))

            if nominatim_items:
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_053d5fdbc9}{len(nominatim_items)}{ZH.S_f136476580}",
                    f"═══ Stage 3: C3 batch Nominatim fallback ({len(nominatim_items)} items) ═══"))
                nom_results = _batch_nominatim_geocode(nominatim_items, max_workers=3)
                nom_success = 0
                for org, country in nominatim_items:
                    key = (org, country)
                    if key in nom_results and nom_results[key]:
                        coords = nom_results[key]
                        # 找到所有使用此 (org, country) 的 cache 条目并更新
                        for addr in unique_c1:
                            if addr in cache:
                                r = cache[addr]
                                if r.get("Organization", "").strip() == org:
                                    r["lat"] = coords["lat"]
                                    r["lng"] = coords["lng"]
                                    nom_success += 1
                                    prog["logs"].append(_tr(lang,
                                        f"{ZH.S_556be01584}{org}",
                                        f"🔗 Nominatim geocoded: {org}"))
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_8bc45d6415}{nom_success}{ZH.S_948623584a}",
                    f"Nominatim fallback done: updated {nom_success} item(s)"))
            else:
                prog["logs"].append(_tr(lang, ZH.S_b219484375,
                                        "═══ Stage 3: C3 no Nominatim fallback needed ═══"))

        # ── 将结果写回 DataFrame（列级批量赋值，避免 pandas 2.x 逐格严格类型检查） ──
        country_vals: Dict[Any, str]   = {}
        org_vals:     Dict[Any, str]   = {}
        city1_vals:   Dict[Any, str]   = {}
        city2_vals:   Dict[Any, str]   = {}
        lat_vals:     Dict[Any, float] = {}
        lng_vals:     Dict[Any, float] = {}
        src_vals:     Dict[Any, str]   = {}
        model_vals:   Dict[Any, str]   = {}

        for idx, row in df.iterrows():
            raw = row.get(field, "")
            v = str(raw).strip() if pd.notna(raw) else ""
            if v and v in cache:
                p = cache[v]
                lat_v = p.get("lat")
                lng_v = p.get("lng")
                country_vals[idx] = str(p.get("Country/Region", "") or "")
                org_vals[idx]     = str(p.get("Organization", "") or "")
                city1_vals[idx]   = str(p.get("City1", "") or "")
                city2_vals[idx]   = str(p.get("City2", "") or "")
                lat_vals[idx]     = float(lat_v) if lat_v is not None else np.nan
                lng_vals[idx]     = float(lng_v) if lng_v is not None else np.nan
                src_vals[idx]     = str(p.get("_src", "") or "")
                model_vals[idx]   = str(p.get("_model", "") or "")
            elif v:
                src_vals[idx]   = "pending"
                model_vals[idx] = "need-other-model"

        for col, val_dict in [(cols["country"], country_vals), (cols["org"], org_vals),
                               (cols["city1"], city1_vals),   (cols["city2"], city2_vals),
                               (cols["src"], src_vals),       (cols["model"], model_vals)]:
            new_col = pd.Series(val_dict, dtype=object)
            df[col] = new_col.reindex(df.index, fill_value=np.nan)

        for col, val_dict in [(cols["lat"], lat_vals), (cols["lng"], lng_vals)]:
            new_col = pd.Series(val_dict, dtype=float)
            df[col] = new_col.reindex(df.index, fill_value=np.nan)

        sessions[sid][_field_parsed_df_key(field)] = df

        if stop_ev.is_set():
            prog["status"]   = "stopped"
            prog["progress"] = int(len(cache) / total * 100)
            prog["logs"].append(_tr(lang, f"{ZH.S_6c308de674}{len(cache)}/{total}{ZH.S_ad29083184}",
                                    f"⏹ Stopped | done {len(cache)}/{total} addresses"))
        else:
            prog["status"]   = "done"
            prog["progress"] = 100
            if unresolved_after_all_models:
                prog["logs"].append(_tr(lang,
                    f"{ZH.S_38ae2fd0ea}{len(unresolved_after_all_models)}{ZH.S_33f7cbbf8b}",
                    f"⚠ {len(unresolved_after_all_models)} addresses still incomplete after final stage, marked as pending"))
            prog["logs"].append(_tr(lang,
                f"{ZH.S_45b2d61cd6}{round_num}{ZH.S_b09e05d890}{len(cache)}/{total}{ZH.S_5c96b9c187}{len(df)}{ZH.S_02b44ef924}",
                f"✅ All done! {round_num} rounds + final stage | success {len(cache)}/{total} | wrote {len(df)} address rows"))

        # 生成解析结果统计
        prog["report"] = {
            "total": total,
            "success": len(cache),
            "failed": len(unresolved_after_all_models),
            "success_rate": round(len(cache) / total * 100, 2) if total > 0 else 0,
        }

    except Exception as e:
        prog["status"] = "error"
        prog["logs"].append(_tr(lang, f"{ZH.S_7449367fa2}{e}", f"Error: {e}"))
        traceback.print_exc()

