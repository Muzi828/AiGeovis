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

from geo.country import COUNTRY_COORDS, _lookup_country_coords, _normalize_country

def _generate_gml(
    nodes: List[Dict],
    edges: List[Dict],
    coord_type: str = "normalized",
    include_matrix: bool = False,
    matrix: List[List[int]] = None,
    entities: List[str] = None,
) -> str:
    """
    将节点和边数据转换为 GML 格式字符串。

    参数
    ───
    nodes          : 节点列表
    edges          : 边列表
    coord_type     : 坐标类型（normalized / geo / none）
    include_matrix : 是否包含邻接矩阵注释
    matrix         : 共现矩阵
    entities       : 实体名称列表
    """
    # 建立 name → id 的映射
    name_to_id = {node["name"]: idx for idx, node in enumerate(nodes)}

    # 计算节点的链接数和总连接强度
    link_counts: Dict[str, int] = {}
    link_strengths: Dict[str, int] = {}

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        w = edge.get("weight", 1)

        link_counts[src] = link_counts.get(src, 0) + 1
        link_counts[tgt] = link_counts.get(tgt, 0) + 1
        link_strengths[src] = link_strengths.get(src, 0) + w
        link_strengths[tgt] = link_strengths.get(tgt, 0) + w

    # 坐标处理
    if coord_type == "normalized":
        _apply_normalized_coords(nodes)
    elif coord_type == "geo":
        _apply_geo_coords(nodes)
    # coord_type == "none" 时不处理坐标

    # 构建 GML 内容
    lines = []
    lines.append('Creator "AiGeovis Entity Matrix Exporter"')
    lines.append("graph")
    lines.append("[")

    # 添加 directed 标志（0 表示无向图）
    lines.append("  directed 0")

    # 生成节点
    for idx, node in enumerate(nodes):
        lines.append("")
        lines.append("  node")
        lines.append("  [")

        # ID 和 Label
        lines.append(f"    id {idx}")
        lines.append(f'    label "{_escape_gml_string(node["name"])}"')

        # 坐标（根据 coord_type）
        if coord_type != "none":
            x = node.get("_gml_x", 0)
            y = node.get("_gml_y", 0)
            lines.append(f"    x {x:.6f}")
            lines.append(f"    y {y:.6f}")

        # 频次
        freq = node.get("frequency", 0)
        lines.append(f"    weight<frequency> {freq}")

        # 链接数
        links = link_counts.get(node["name"], 0)
        lines.append(f"    weight<links> {links}")

        # 总连接强度
        strength = link_strengths.get(node["name"], 0)
        lines.append(f"    weight<total_link_strength> {strength}")

        # 如果是 geo 模式，额外输出经纬度
        if coord_type == "geo" and node.get("lat") is not None and node.get("lng") is not None:
            lines.append(f"    geo<lat> {node['lat']:.6f}")
            lines.append(f"    geo<lng> {node['lng']:.6f}")

        lines.append("  ]")

    # 生成边
    for edge in edges:
        src_id = name_to_id.get(edge["source"])
        tgt_id = name_to_id.get(edge["target"])

        if src_id is None or tgt_id is None:
            continue

        lines.append("")
        lines.append("  edge")
        lines.append("  [")
        lines.append(f"    source {src_id}")
        lines.append(f"    target {tgt_id}")
        lines.append(f"    value {edge.get('weight', 1):.1f}")
        lines.append("  ]")

    # 添加邻接矩阵注释（可选）
    if include_matrix and matrix and entities:
        lines.append("")
        lines.append("  /* Co-occurrence Matrix */")
        lines.append("  /*")
        lines.append(f"  matrix_dim {len(entities)}")
        # f-string 内不能有反斜杠，需要先构造字符串
        escaped_labels = [_escape_gml_string(e) for e in entities]
        labels_str = '  matrix_labels ["' + '", "'.join(escaped_labels) + '"]'
        lines.append(labels_str)
        lines.append("  matrix_values [")

        for row_idx, row in enumerate(matrix):
            row_str = "    [" + ", ".join(str(v) for v in row) + "]"
            if row_idx < len(matrix) - 1:
                row_str += ","
            lines.append(row_str)

        lines.append("  ]")
        lines.append("  */")

    lines.append("]")

    return "\n".join(lines) + "\n"

def _apply_normalized_coords(nodes: List[Dict]) -> None:
    """
    将节点的经纬度标准化到 [-1, 1] 范围。
    """
    # 收集有效的经纬度
    valid_nodes = [(n, n.get("lat"), n.get("lng"))
                   for n in nodes
                   if n.get("lat") is not None and n.get("lng") is not None]

    if not valid_nodes:
        # 没有有效坐标，全部设为 (0, 0)
        for node in nodes:
            node["_gml_x"] = 0.0
            node["_gml_y"] = 0.0
        return

    lats = [v[1] for v in valid_nodes]
    lngs = [v[2] for v in valid_nodes]

    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    lat_range = max_lat - min_lat if max_lat != min_lat else 1
    lng_range = max_lng - min_lng if max_lng != min_lng else 1

    # 建立已处理的节点集合（避免重复设置）
    processed = set()

    for node, lat, lng in valid_nodes:
        if node["name"] not in processed:
            node["_gml_x"] = (lng - min_lng) / lng_range * 2 - 1
            node["_gml_y"] = (lat - min_lat) / lat_range * 2 - 1
            processed.add(node["name"])

    # 没有坐标的节点设为 (0, 0)
    for node in nodes:
        if node["name"] not in processed:
            node["_gml_x"] = 0.0
            node["_gml_y"] = 0.0

def _apply_geo_coords(nodes: List[Dict]) -> None:
    """
    直接使用经纬度作为坐标。
    """
    for node in nodes:
        node["_gml_x"] = node.get("lng", 0) if node.get("lng") is not None else 0
        node["_gml_y"] = node.get("lat", 0) if node.get("lat") is not None else 0

def _escape_gml_string(s: str) -> str:
    """
    转义 GML 字符串中的特殊字符。
    """
    if s is None:
        return ""
    # 转义双引号和反斜杠
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return s

