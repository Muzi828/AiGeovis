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


@router.post("/api/data/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail=ZH.S_46edf8b789)

    # 把所有文件内容读入内存，再写入临时目录
    file_data: List[tuple] = []
    for f in files:
        content = await f.read()
        file_data.append((f.filename or f"file_{uuid.uuid4().hex}.txt", content))

    tmp_dir = tempfile.mkdtemp(prefix="geocode_upload_")
    for name, content in file_data:
        with open(os.path.join(tmp_dir, name), "wb") as fp:
            fp.write(content)

    # ── 检测文件类型 ──────────────────────────────
    first_file_name, first_content = file_data[0]
    if Path(first_file_name).suffix.lower() in _LOCAL_ADDR_EXTS:
        # 本地地址文件（CSV/XLSX）：按扩展名优先判定，避免对二进制内容做文本探测
        file_type = "local_address"
    else:
        first_line = first_content.decode("utf-8", errors="ignore").split("\n")[0]
        file_type = _detect_file_type(first_line, first_file_name)

    sid = uuid.uuid4().hex

    if file_type == "local_address":
        # ── 本地地址文件：拆出机构（地址）/国家子类型，并入 affiliation 流程 ──
        # 机构列与国家列各自成为一个子类型；解析时两者都会先查固定参考库（增量匹配）。
        org_frames: List[pd.DataFrame] = []
        country_frames: List[pd.DataFrame] = []

        def _valid_mask(series: pd.Series) -> pd.Series:
            s = series.astype(str).str.strip()
            return s.ne("") & ~s.str.lower().isin(("nan", "none"))

        for fname, _ in file_data:
            if Path(fname).suffix.lower() not in _LOCAL_ADDR_EXTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"{ZH.S_d8f81ea417}{fname}",
                )
            try:
                df_raw = _parse_local_address_file(tmp_dir, fname)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"{ZH.S_7e5c223dfb}{fname}]: {e}")

            # 机构（地址）子类型
            if "name" in df_raw.columns:
                sub = df_raw[_valid_mask(df_raw["name"])]
                if not sub.empty:
                    df_o = pd.DataFrame()
                    df_o["Organization"] = sub["name"].values
                    df_o["lat"] = sub["lat"].values if "lat" in sub.columns else np.nan
                    df_o["lng"] = sub["lng"].values if "lng" in sub.columns else np.nan
                    df_o["count"] = sub["count"].values
                    has_row_coords = (
                        pd.to_numeric(df_o["lat"], errors="coerce").notna()
                        & pd.to_numeric(df_o["lng"], errors="coerce").notna()
                    )
                    df_o["ParseSrc"] = np.where(has_row_coords, "file", "pending")
                    df_o["ParseModel"] = np.where(has_row_coords, "upload-coords", "")
                    df_o["_affiliation_type"] = "affiliation_org"
                    org_frames.append(df_o)

            # 国家子类型（存在国家列时）：坐标一律置空，交由参考库/大模型解析
            if "country" in df_raw.columns:
                subc = df_raw[_valid_mask(df_raw["country"])]
                if not subc.empty:
                    df_c = pd.DataFrame()
                    df_c["Country/Region"] = subc["country"].values
                    df_c["lat"] = np.nan
                    df_c["lng"] = np.nan
                    df_c["count"] = subc["count"].values
                    df_c["ParseSrc"] = "pending"
                    df_c["ParseModel"] = ""
                    df_c["_affiliation_type"] = "affiliation_country"
                    country_frames.append(df_c)

        if not org_frames and not country_frames:
            raise HTTPException(status_code=400, detail=ZH.S_83d996b971)

        org_merged = (
            pd.concat(org_frames, ignore_index=True) if org_frames
            else pd.DataFrame(columns=["Organization", "lat", "lng", "count",
                                       "ParseSrc", "ParseModel", "_affiliation_type"])
        )
        org_has_coords = bool(
            not org_merged.empty
            and pd.to_numeric(org_merged["lat"], errors="coerce").notna().any()
            and pd.to_numeric(org_merged["lng"], errors="coerce").notna().any()
        )
        has_country_subtype = bool(country_frames)

        # 仅当「只有机构且机构自带坐标」时才直接可视化（pre_parsed）；
        # 一旦存在国家子类型，就必须走解析以完成参考库匹配。
        pre_parsed = org_has_coords and not has_country_subtype

        subtypes: List[str] = []
        frames: List[pd.DataFrame] = []
        if not org_merged.empty:
            frames.append(org_merged)
            subtypes.append("affiliation_org")
        if has_country_subtype:
            frames.append(pd.concat(country_frames, ignore_index=True))
            subtypes.append("affiliation_country")
        df_merged = pd.concat(frames, ignore_index=True)

        if pre_parsed:
            parsed_org = pd.DataFrame({
                "Organization": org_merged["Organization"].values,
                "lat": org_merged["lat"].values,
                "lng": org_merged["lng"].values,
                "count": org_merged["count"].values,
                "ParseSrc": org_merged["ParseSrc"].values,
                "ParseModel": org_merged["ParseModel"].values,
            })
        else:
            parsed_org = pd.DataFrame(
                columns=["Organization", "lat", "lng", "count", "ParseSrc", "ParseModel"]
            )

        empty_country = pd.DataFrame(columns=["Country/Region", "lat", "lng", "count", "ParseSrc", "ParseModel"])
        empty_city = pd.DataFrame(columns=["City1", "lat", "lng", "count", "ParseSrc", "ParseModel"])

        sessions[sid] = {
            "df":                              df_merged,
            "file_type":                       "affiliation",
            "source_type":                     "local_address",
            "affiliation_subtypes":             subtypes,
            "parsed_df_affiliation_country":    empty_country.copy(),
            "parsed_df_affiliation_org":        parsed_org,
            "parsed_df_affiliation_city":       empty_city.copy(),
            "tmp_dir":                         tmp_dir,
            "record_count":                    len(df_merged),
            "loaded_at":                       time_module.time(),
            "pre_parsed":                      pre_parsed,
        }

        if has_country_subtype:
            columns = ["name", "country", "count"]
        elif pre_parsed:
            columns = ["name", "count", "lat", "lng"]
        else:
            columns = ["name", "count"]

        return {
            "session_id":   sid,
            "record_count": len(df_merged),
            "columns":      columns,
            "files":        [n for n, _ in file_data],
            "file_type":    "affiliation",
            "source_type":  "local_address",
            "affiliation_subtypes": subtypes,
            "pre_parsed":   pre_parsed,
        }

    if file_type.startswith("affiliation"):
        # ── affiliation 类型：支持多文件，一次性解析所有子类型 ──
        # 遍历所有上传文件，按子类型解析后合并为一个 DataFrame
        all_dfs: List[pd.DataFrame] = []
        detected_subtypes: List[str] = []

        for fname, fcontent in file_data:
            first_l = fcontent.decode("utf-8", errors="ignore").split("\n")[0]
            subtype = _detect_affiliation_subtype(first_l, fname)
            try:
                df_raw = _parse_affiliation_file(tmp_dir, fname)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"{ZH.S_7e5c223dfb}{fname}]: {e}")

            if subtype == "affiliation_country":
                name_col = "Country/Region"
            elif subtype == "affiliation_city":
                name_col = "City1"
            else:
                name_col = "Organization"

            df_i = pd.DataFrame()
            df_i[name_col] = df_raw["name"].values
            df_i["lat"] = np.nan
            df_i["lng"] = np.nan
            df_i["count"] = df_raw["count"].values
            df_i["ParseSrc"] = "pending"
            df_i["ParseModel"] = ""
            df_i["_affiliation_type"] = subtype
            all_dfs.append(df_i)
            detected_subtypes.append(subtype)

        # 合并所有子类型为一个 DataFrame
        if not all_dfs:
            raise HTTPException(status_code=400, detail=ZH.S_b4e7c25ad8)

        df_merged = pd.concat(all_dfs, ignore_index=True)

        # 三个子类型的 DataFrame（初始均为空，解析后填充）
        empty_country = pd.DataFrame(columns=["Country/Region", "lat", "lng", "count", "ParseSrc", "ParseModel"])
        empty_org     = pd.DataFrame(columns=["Organization", "lat", "lng", "count", "ParseSrc", "ParseModel"])
        empty_city    = pd.DataFrame(columns=["City1", "lat", "lng", "count", "ParseSrc", "ParseModel"])

        sessions[sid] = {
            "df":                              df_merged,
            "file_type":                       "affiliation",
            "affiliation_subtypes":             detected_subtypes,
            "parsed_df_affiliation_country":    empty_country.copy(),
            "parsed_df_affiliation_org":        empty_org.copy(),
            "parsed_df_affiliation_city":       empty_city.copy(),
            "tmp_dir":                         tmp_dir,
            "record_count":                    len(df_merged),
            "loaded_at":                       time_module.time(),
        }

        return {
            "session_id":   sid,
            "record_count": len(df_merged),
            "columns":      ["name", "count"],
            "files":        [n for n, _ in file_data],
            "file_type":    "affiliation",
            "affiliation_subtypes": detected_subtypes,
        }

    else:
        # ── WoS/BP 类型：走原有 DataService 解析 ──
        try:
            paths = list(Path(tmp_dir).iterdir())
            df = await (_load_with_dataservice_async(str(paths[0]), False)
                        if len(paths) == 1
                        else _load_with_dataservice_async(tmp_dir, True))
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"{ZH.S_99c6262c4f}{e}")

        sessions[sid] = {
            "df":           df,
            "file_type":    "wos",
            "tmp_dir":      tmp_dir,
            "record_count": len(df),
            "loaded_at":    time_module.time(),
        }

        avail_cols = [c for c in df.columns if df[c].astype(str).str.strip().ne("").any()]
        return {
            "session_id":   sid,
            "record_count": len(df),
            "columns":      avail_cols,
            "files":        [n for n, _ in file_data],
            "file_type":    "wos",
        }

@router.get("/api/data/records")
def get_records(session_id: str, page: int = 1, page_size: int = 50):
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    return df_page(sess["df"], page, page_size)

@router.get("/api/data/summary")
def get_summary(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    df = sess["df"]

    def top_n(col, n=10):
        if col not in df.columns:
            return []
        s = df[col].dropna().astype(str)
        s = s[s.str.strip() != ""]
        vc = s.value_counts().head(n)
        return [{"name": k, "value": int(v)} for k, v in vc.items()]

    year_dist = []
    if "PY" in df.columns:
        ys = pd.to_numeric(df["PY"], errors="coerce").dropna().astype(int)
        vc = ys.value_counts().sort_index()
        year_dist = [{"year": int(y), "count": int(c)} for y, c in vc.items()]

    return {
        "record_count": len(df),
        "year_distribution": year_dist,
        "top_sources": top_n("SO", 10),
        "document_types": top_n("DT", 8),
        "top_keywords": top_n("DE", 15),
    }

@router.get("/api/data/export")
def export_csv(session_id: str):
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    import io
    buf = io.StringIO()
    sess["df"].copy().fillna("").to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=wos_data.csv"},
    )

@router.get("/api/data/quality")
def data_quality(session_id: str):
    """Field completeness and data overview statistics (mirrors the desktop Data Quality panel)."""
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    if sess.get("file_type") == "affiliation":
        raise HTTPException(status_code=400, detail=ZH.S_152dad9f20)
    df = sess["df"]
    n = len(df)

    # ── 字段完整性 ──
    completeness = []
    for tag, label in _QUALITY_FIELDS:
        if tag in df.columns:
            s = df[tag]
            missing = int((s.isna() | s.astype(str).str.strip().eq("")).sum())
        else:
            missing = n
        rate = missing / n * 100 if n else 0.0
        status = ("excellent" if rate == 0 else
                  "good" if rate <= 10 else
                  "acceptable" if rate <= 20 else "poor")
        completeness.append({
            "field": tag, "label": label, "missing": missing,
            "missing_rate": round(rate, 2), "status": status,
        })

    # ── 概览统计 ──
    stats: Dict[str, Any] = {"documents": n}

    if "PY" in df.columns:
        years = pd.to_numeric(df["PY"], errors="coerce").dropna().astype(int)
        if not years.empty:
            stats["timespan"] = f"{int(years.min())}-{int(years.max())}"

    if "SO" in df.columns:
        stats["sources"] = int(df["SO"].dropna().astype(str).str.strip().replace("", np.nan).dropna().nunique())
    if "DT" in df.columns:
        stats["document_types"] = int(df["DT"].dropna().astype(str).str.strip().replace("", np.nan).dropna().nunique())
    if "AU" in df.columns:
        stats["authors"] = int(_split_multi(df["AU"]).nunique())
    if "DE" in df.columns:
        stats["author_keywords"] = int(_split_multi(df["DE"]).nunique())
    if "ID" in df.columns:
        stats["keywords_plus"] = int(_split_multi(df["ID"]).nunique())

    # C1 派生：机构（地址首段）与国家（地址末段，经别名归一）
    if "C1" in df.columns:
        orgs: set = set()
        intl_docs = 0
        countries: set = set()
        for val in df["C1"]:
            addrs = _split_address_cell(val)
            doc_countries = set()
            for addr in addrs:
                parts = [p.strip() for p in addr.split(",") if p.strip()]
                if parts:
                    orgs.add(parts[0])
                    doc_countries.add(_normalize_country(parts[-1]))
            countries.update(doc_countries)
            if len(doc_countries) > 1:
                intl_docs += 1
        stats["institutions"] = len(orgs)
        stats["countries"] = len(countries)
        c1_docs = int(df["C1"].dropna().astype(str).str.strip().ne("").sum())
        stats["international_coauthorship_pct"] = (
            round(intl_docs / c1_docs * 100, 2) if c1_docs else 0.0
        )

    if "TC" in df.columns:
        tc = pd.to_numeric(df["TC"], errors="coerce").fillna(0).astype(int)
        stats["total_citations"] = int(tc.sum())
        stats["avg_citations"] = round(float(tc.mean()), 2) if n else 0.0
        cites = sorted(tc.tolist(), reverse=True)
        h = 0
        for i, c in enumerate(cites, start=1):
            if c >= i:
                h = i
            else:
                break
        stats["h_index"] = h

    return {"record_count": n, "completeness": completeness, "stats": stats}

@router.get("/api/data/duplicates")
def detect_duplicates(session_id: str, method: str = "doi"):
    """Detect duplicate publication records. method: doi (by DOI) | doi_ti (by DOI + title)."""
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    if sess.get("file_type") == "affiliation":
        raise HTTPException(status_code=400, detail=ZH.S_d2d3fe41a7)
    df = sess["df"].reset_index(drop=True)

    groups_out = []
    for gid, g in enumerate(_duplicate_groups(df, method), start=1):
        records = []
        for pos in g:
            row = df.iloc[pos]
            records.append({
                "index": int(pos),
                "title": str(row.get("TI", "") or ""),
                "authors": str(row.get("AU", "") or "")[:120],
                "year": str(row.get("PY", "") or ""),
                "doi": str(row.get("DI", "") or ""),
            })
        groups_out.append({"group": gid, "records": records})

    dup_rows = sum(len(g["records"]) - 1 for g in groups_out)
    return {"method": method, "group_count": len(groups_out),
            "duplicate_rows": dup_rows, "groups": groups_out}

@router.post("/api/data/duplicates/remove")
def remove_duplicates(req: DuplicateRemoveRequest):
    """Remove duplicate records: pass `indices` to delete exactly those, otherwise keep the
    first record of each group and delete the rest. Existing parse results become invalid
    after deletion and must be re-parsed."""
    sess = sessions.get(req.session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    if sess.get("file_type") == "affiliation":
        raise HTTPException(status_code=400, detail=ZH.S_d2d3fe41a7)
    df = sess["df"].reset_index(drop=True)

    if req.indices:
        to_drop = [i for i in set(req.indices) if 0 <= i < len(df)]
    else:
        to_drop = []
        for g in _duplicate_groups(df, req.method):
            to_drop.extend(g[1:])  # 保留每组第一条

    new_df = df.drop(index=to_drop).reset_index(drop=True)
    sess["df"] = new_df
    sess["record_count"] = len(new_df)
    # 原始数据已变化，清除既有解析结果，避免行号错位
    for key in [k for k in list(sess.keys()) if k.startswith("parsed_df_")]:
        sess.pop(key, None)

    return {"removed": len(to_drop), "record_count": len(new_df),
            "note": ZH.S_c9085a5de6}

@router.delete("/api/data/session")
def delete_session(session_id: str):
    """Clear the in-memory data for the given session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    sessions.pop(session_id, None)
    parse_progress.pop(session_id, None)
    stop_flags.pop(session_id, None)
    return {"message": ZH.S_8604bedd31, "session_id": session_id}

@router.delete("/api/data/sessions")
def delete_all_sessions():
    """Clear all sessions, parse progress, and stop flags."""
    session_count = len(sessions)
    sessions.clear()
    parse_progress.clear()
    stop_flags.clear()
    return {"message": ZH.S_307fa0eb3b, "sessions": session_count}

@router.get("/api/data/session-info")
def session_info(session_id: str):
    """Validate whether a session is still valid (used when the frontend reloads)."""
    sess = sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail=ZH.S_a535de215b)
    # 检查哪些字段已完成解析
    parsed_fields = {}
    file_type = sess.get("file_type", "wos")

    if file_type == "affiliation":
        # affiliation 类型：三个子类型均已初始化，报告各自的解析进度
        for subtype_key in ("affiliation_country", "affiliation_org", "affiliation_city"):
            parsed_df = sess.get(f"parsed_df_{subtype_key}")
            if parsed_df is not None and not parsed_df.empty:
                total = int(len(parsed_df))
                done = int(
                    (
                        parsed_df["lat"].notna() & parsed_df["lng"].notna() &
                        ((parsed_df["lat"].abs() > 1e-9) | (parsed_df["lng"].abs() > 1e-9))
                    ).sum()
                )
                parsed_fields[subtype_key] = {"total": total, "parsed": done}
            else:
                parsed_fields[subtype_key] = {"total": 0, "parsed": 0}
    else:
        for fld in ("C1", "C3"):
            df = _get_field_df(sess, fld)
            c = _field_cols(fld)["country"]
            if c in df.columns:
                total   = int(df[fld].dropna().astype(str).str.strip().ne("").sum()
                             if fld in df.columns else 0)
                done    = int(df[c].astype(str).str.strip().ne("").sum())
                parsed_fields[fld] = {"total": total, "parsed": done}
    return {
        "session_id":   session_id,
        "file_type":    file_type,
        "record_count": sess["record_count"],
        "parsed_fields": parsed_fields,
    }

