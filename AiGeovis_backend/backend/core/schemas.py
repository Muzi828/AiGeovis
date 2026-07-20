from __future__ import annotations

from typing import List
from pydantic import BaseModel

class AIConfig(BaseModel):
    type: str = "official"       # "official" | "local"
    provider: str = "OpenAI"
    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o-mini"
    name: str = ""               # 显示名称（可选）

class ParseC1Request(BaseModel):
    session_id: str
    ai_configs: List[AIConfig]   # 多个模型配置
    batch_size: int = 30
    field: str = "C1"            # 解析目标字段："C1" 或 "C3"
    skip_cache: bool = False     # True=忽略固定参考库，全部交由大模型解析（全量解析）；C3 默认先查库
    lang: str = "zh"             # 进度日志语言："zh" / "en"

class GeocodeRequest(BaseModel):
    session_id: str
    amap_key: str = ""
    use_nominatim: bool = True
    field: str = "C1"            # 使用哪个字段的解析结果做地理编码
    tier: str = ""               # 可选：指定分层解析表（country/city/org），空则用整体解析表

class ListModelsRequest(BaseModel):
    type: str = "official"
    provider: str = "OpenAI"
    api_key: str = ""
    base_url: str = ""

class ParseTierRequest(BaseModel):
    """Tiered parse request: parse a single tier (country / city / organization)."""
    session_id: str
    ai_configs: List[AIConfig]
    batch_size: int = 30
    field: str = "C1"       # "C1" 或 "C3"
    tier: str = "country"   # "country" | "city" | "org"
    skip_cache: bool = False  # True=忽略固定参考库，全部交由大模型解析（全量解析）
    lang: str = "zh"          # 进度日志语言："zh" / "en"

class ParseBatchTiersRequest(BaseModel):
    """Batch tiered parse request: parse multiple tiers (country / city / organization) at once."""
    session_id: str
    ai_configs: List[AIConfig]
    batch_size: int = 30
    field: str = "C1"            # "C1" 或 "C3"
    tiers: List[str]              # ["country"] 或 ["country", "city"] 或 ["country", "city", "org"]
    skip_cache: bool = False      # True=忽略固定参考库，全部交由大模型解析（全量解析）
    lang: str = "zh"              # 进度日志语言："zh" / "en"

class StatsRequest(BaseModel):
    """Statistics aggregation request."""
    session_id: str
    field: str = "C1"
    tier: str = "country"    # "country" | "city" | "org"
    top_n: int = 30

class BenchmarkRequest(BaseModel):
    type: str = "official"
    provider: str = "OpenAI"
    api_key: str = ""
    base_url: str = ""
    timeout: float = 3.0     # 判定"通过"的最大响应时间（秒）
    max_workers: int = 10    # 并发数

class DuplicateRemoveRequest(BaseModel):
    session_id: str
    method: str = "doi"       # "doi" | "doi_ti"
    indices: List[int] = []   # 显式待删除的行号；为空时每组自动保留第一条

class ParseAffiliationRequest(BaseModel):
    session_id: str
    ai_configs: List[AIConfig]
    batch_size: int = 20
    skip_cache: bool = False  # True=忽略本地缓存，强制用大模型重算
    lang: str = "zh"          # 进度日志语言："zh" / "en"

