from __future__ import annotations

import json
from typing import Dict

import pandas as pd

from geo.country import _normalize_country

def df_page(df: pd.DataFrame, page: int, page_size: int) -> Dict:
    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    chunk = df.iloc[start:end].copy().fillna("").astype(str)
    return {"total": total, "page": page, "page_size": page_size,
            "records": chunk.to_dict(orient="records")}

def parse_ai_json(text: str) -> Dict:
    """解析 AI 返回的 JSON，同时处理 lat/lng 数值字段，并标准化国家名。

    使用 json.JSONDecoder(raw=True=True) 配合 count=0 实现"从任意位置自动跳过非JSON前缀"，
    比正则提取更健壮，不会因为字符串内容含 } 或 { 而匹配错误。
    """
    defaults = {
        "Country/Region": "", "Organization": "", "City1": "", "City2": "",
        "lat": None, "lng": None,
    }
    try:
        # 尝试直接解析（AI 正常返回完整 JSON 的情况）
        obj = json.loads(text.strip())
        defaults.update(obj)
    except json.JSONDecodeError:
        # JSON 前可能有不纯文本（如 markdown 代码块标记），用 json.JSONDecoder 跳过前缀
        try:
            decoder = json.JSONDecoder(raw=True)
            obj, _ = decoder.raw_decode(text)
            defaults.update(obj)
        except (json.JSONDecodeError, ValueError):
            # 仍然失败，返回空 defaults
            pass

    # 确保 lat/lng 为 float 或 None
    for k in ("lat", "lng"):
        v = defaults[k]
        try:
            defaults[k] = float(v) if v not in (None, "", "null") else None
        except (TypeError, ValueError):
            defaults[k] = None

    # 标准化国家/地区名称
    if defaults.get("Country/Region"):
        defaults["Country/Region"] = _normalize_country(defaults["Country/Region"])

    return defaults

