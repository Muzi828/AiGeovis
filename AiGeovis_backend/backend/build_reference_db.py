# -*- coding: utf-8 -*-
"""
构建 Affiliation 只读参考库 affiliation_cache.db。

数据来源：deepseek-v4-pro 全量坐标数据集的三份 CSV
    - coords_countries.csv    国家/地区 → 经纬度
    - coords_affiliations.csv 机构（WoS C3 缩写大写名） → 经纬度
    - coords_affil_dept.csv   机构（含院系，Title Case 全称） → 经纬度
    （原始表不含城市，故本库只服务于国家 / 机构匹配。）

处理规则：
    1) 剔除无效地址：coord_valid != 1、经纬度缺失、经纬度为 (0,0)、越界、名称为空。
    2) 大小写不敏感匹配：主键 name 存「去空格 + 转小写」的规范 key；
       同时保留一列 name_orig 存 CSV 原始名称，仅供溯源（不参与匹配、不参与显示）。
    3) 去重：按小写 key 去重，冲突时保留 count 更大的一条（更具代表性的坐标）；
       count 相同则按 country > affiliation > dept 的优先级保留。

匹配时（见 main.py::_affiliation_cache_get）：把用户解析出的名称同样转小写后精确查主键。
命中后仅取 lat/lng，显示仍沿用用户上传数据的原始大小写。

用法：
    python build_reference_db.py                # 使用默认 CSV 路径
    python build_reference_db.py <csv_dir>      # 指定 CSV 所在目录
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

from core.i18n import ZH

# Windows GBK stdout 兼容
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

BACKEND_DIR = Path(__file__).resolve().parent
CACHE_DB = BACKEND_DIR / "affiliation_cache.db"

# 离线重建 affiliation_cache.db 时的默认 CSV 目录（不在本仓库内；
# 运行时可传参覆盖：python build_reference_db.py <csv_dir>）。
# 与前端/后端运行时使用的 demoData 示例数据无关。
DEFAULT_CSV_DIR = Path(
    r"d:\Work\Papers\GeoData\论文稿件\AiGeovis数据论文交付\全量坐标数据集\deepseek-v4-pro"
)

# (文件名, 类别标签, 优先级)  —— 优先级数字越小越优先
CSV_SOURCES = [
    ("coords_countries.csv", "country", 0),
    ("coords_affiliations.csv", "org", 1),
    ("coords_affil_dept.csv", "dept", 2),
]

MODEL_TAG = "deepseek-v4-pro"


def _to_float(s):
    try:
        v = float(str(s).strip())
        return v
    except (TypeError, ValueError):
        return None


def _is_valid(lat, lng, coord_valid, name):
    if not name:
        return False
    if str(coord_valid).strip() != "1":
        return False
    if lat is None or lng is None:
        return False
    if abs(lat) < 1e-9 and abs(lng) < 1e-9:
        return False
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
        return False
    return True


def _read_csv_rows(path: Path):
    """逐行读取 CSV，返回 [(name_orig, lat, lng, coord_valid, count), ...]"""
    raw = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    if text is None:
        raise ValueError(f"{ZH.S_924f26926c}{path}")

    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [(c or "").strip() for c in (reader.fieldnames or [])]
    out = []
    for row in reader:
        name = (row.get("name") or "").strip()
        lat = _to_float(row.get("lat"))
        lng = _to_float(row.get("lng"))
        cv = (row.get("coord_valid") or "").strip()
        try:
            count = int(float((row.get("count") or "0").strip()))
        except (TypeError, ValueError):
            count = 0
        out.append((name, lat, lng, cv, count))
    return out


def build():
    csv_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV_DIR
    print(f"{ZH.S_1e700221f9}{csv_dir}")
    print(f"{ZH.S_74f0a70b5e}{CACHE_DB}")

    # key(lower) -> dict(row)
    best = {}
    stats = {}

    for fname, kind, prio in CSV_SOURCES:
        fp = csv_dir / fname
        if not fp.exists():
            print(f"{ZH.S_1d4c92c776}{fp}")
            continue
        rows = _read_csv_rows(fp)
        total = len(rows)
        kept = 0
        dropped = 0
        for name, lat, lng, cv, count in rows:
            if not _is_valid(lat, lng, cv, name):
                dropped += 1
                continue
            key = name.lower()
            cur = best.get(key)
            if cur is None:
                best[key] = {
                    "key": key, "name_orig": name, "lat": lat, "lng": lng,
                    "count": count, "prio": prio, "kind": kind,
                }
                kept += 1
            else:
                # 冲突：保留 count 更大者；count 相同保留优先级更高（prio 更小）者
                if count > cur["count"] or (count == cur["count"] and prio < cur["prio"]):
                    best[key] = {
                        "key": key, "name_orig": name, "lat": lat, "lng": lng,
                        "count": count, "prio": prio, "kind": kind,
                    }
        stats[fname] = (total, kept, dropped)
        print(f"[INFO] {fname}{ZH.S_4f87bfbbc5}{total}{ZH.S_501555462c}{kept}{ZH.S_20c109e4a8}{dropped}")

    if not best:
        print(ZH.S_532e60f345)
        return

    print(f"{ZH.S_9e5417e701}{len(best):,}{ZH.S_948623584a}")

    # 写入 SQLite（原子替换：先写临时表结构，再整体替换）
    conn = sqlite3.connect(str(CACHE_DB))
    try:
        # 单文件库：使用普通回滚日志，避免只读查询时生成 -wal/-shm 边车文件
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("DROP TABLE IF EXISTS affiliation_cache")
        conn.execute("""
            CREATE TABLE affiliation_cache (
                name      TEXT PRIMARY KEY,   -- normalized match key (strip + lower)
                lat       REAL,
                lng       REAL,
                src       TEXT DEFAULT '',    -- kind: country/org/dept
                model     TEXT DEFAULT '',    -- source model tag
                name_orig TEXT DEFAULT ''     -- original CSV name (trace only)
            )
        """)
        conn.execute("CREATE INDEX idx_name ON affiliation_cache(name)")

        rows_to_insert = [
            (v["key"], v["lat"], v["lng"], v["kind"], MODEL_TAG, v["name_orig"])
            for v in best.values()
        ]
        BATCH = 5000
        for i in range(0, len(rows_to_insert), BATCH):
            conn.executemany(
                "INSERT OR IGNORE INTO affiliation_cache "
                "(name, lat, lng, src, model, name_orig) VALUES (?, ?, ?, ?, ?, ?)",
                rows_to_insert[i:i + BATCH],
            )
            conn.commit()
        conn.execute("VACUUM")
        final = conn.execute("SELECT COUNT(*) FROM affiliation_cache").fetchone()[0]
        by_kind = dict(conn.execute(
            "SELECT src, COUNT(*) FROM affiliation_cache GROUP BY src"
        ).fetchall())
    finally:
        conn.close()

    size_mb = CACHE_DB.stat().st_size / (1024 * 1024)
    print('\n' + ZH.S_8fea440ed1)
    print(f"{ZH.S_9a17f1fc99}{final:,}")
    print(f"{ZH.S_a3682655b9}{by_kind}")
    print(f"{ZH.S_84e5ead8ee}{size_mb:.1f} MB")


if __name__ == "__main__":
    build()
