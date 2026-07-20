# Affiliation 类型文件 API 文档

> 本文档描述 affiliation 类型（国家列表 / 机构列表 / 城市列表）的完整 API 流程，供前端对接使用。
>
> **前置说明**：本类型与原有的 WoS/C1/C3 类型完全独立，共用一套返回格式，前端可直接复用 C1 的渲染逻辑。

---

## 目录

1. [文件上传](#1-文件上传)
2. [查询原始数据](#2-查询原始数据)
3. [获取 Session 信息](#3-获取-session-信息)
4. [AI 解析](#4-ai-解析)
5. [查询解析进度](#5-查询解析进度)
6. [停止解析](#6-停止解析)
7. [查询解析结果](#7-查询解析结果)
8. [获取可视化数据](#8-获取可视化数据)
9. [清除 Session](#9-清除-session)

---

## 1. 文件上传

### 请求

```
POST /api/data/upload
Content-Type: multipart/form-data
```

一次上传 **三个文件**（三个文件都是 affiliation 类型时才走此流程）：

| 文件 | 识别类型 | 说明 |
|---|---|---|
| `Countries.txt` | `affiliation_country` | 国家列表 |
| `Affiliations.txt` | `affiliation_org` | 机构列表 |
| `Affiliation with Department.txt` | `affiliation_org` | 含院系的机构列表 |

> `Affiliation with Department` 识别为机构，暂不使用城市类型。未来如有城市级别数据，再单独区分。

### 响应

```json
{
  "session_id": "6e9c9d5011f946498cbb237ed364821d",
  "record_count": 244,
  "columns": ["name", "count"],
  "files": [
    "Countries.txt",
    "Affiliations.txt",
    "Affiliation with Department.txt"
  ],
  "file_type": "affiliation",
  "affiliation_subtypes": [
    "affiliation_country",
    "affiliation_org",
    "affiliation_org"
  ]
}
```

### 关键字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | string | **整个流程的唯一凭证**，后续所有接口都需要传入此 ID |
| `record_count` | int | 合并后三条文件的记录总数 |
| `file_type` | string | 文件类型标识，**前端用它判断走哪套逻辑**：`"affiliation"` 表示 affiliation 类型，`"wos"` 表示 WoS/C1 类型 |
| `affiliation_subtypes` | array | 本次上传检测到的子类型列表，可能出现重复值（本次上传了两个机构文件），**前端用它决定展示哪些 tab** |

### 前端区分字段类型的判断逻辑

```javascript
const response = await uploadFiles(files);

// 1. 根据 file_type 判断是 affiliation 还是 wos
if (response.file_type === "affiliation") {
  // → 进入 affiliation 流程
  const sessionId = response.session_id;

  // 2. 根据 affiliation_subtypes 确定有哪些类型的 tab
  // 本次返回 ["affiliation_country", "affiliation_org", "affiliation_org"]
  // 去重后有 ["affiliation_country", "affiliation_org"]
  const uniqueSubtypes = [...new Set(response.affiliation_subtypes)];
  // uniqueSubtypes = ["affiliation_country", "affiliation_org"]

  // 3. 调用解析 / 查询结果时，field 参数传对应值
  // 查询国家结果  → field = "affiliation_country"
  // 查询机构结果  → field = "affiliation_org"
  // 查询城市结果  → field = "affiliation_city"（如有数据）
} else {
  // → 进入原有的 C1 / C3 / WoS 流程
}
```

### file_type 完整对照表

| file_type 值 | 数据类型 | 对应接口 |
|---|---|---|
| `"affiliation"` | 国家 / 机构 / 城市列表文件 | 解析用 `parse-affiliation`，查询用 `field` 参数区分类型 |
| `"wos"` | WoS / BP 文献数据 | 解析用 `parse-c1` / `parse-c3`，查询用 `field=C1` / `field=C3` |

### affiliation_subtypes 与 field 参数对照表

| affiliation_subtypes 值 | 对应 field 参数 | 说明 |
|---|---|---|
| `"affiliation_country"` | `field=affiliation_country` | 国家数据 |
| `"affiliation_org"` | `field=affiliation_org` | 机构数据 |
| `"affiliation_city"` | `field=affiliation_city` | 城市数据（暂未使用，预留） |

---

## 2. 查询原始数据

### 请求

```
GET /api/data/records
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |
| `page` | int | ❌ | 页码，默认 1 |
| `page_size` | int | ❌ | 每页条数，默认 50 |

### 响应

```json
{
  "total": 244,
  "page": 1,
  "page_size": 50,
  "records": [
    {
      "name": "AFGHANISTAN",
      "count": 5511,
      "_affiliation_type": "affiliation_country"
    }
  ]
}
```

> `_affiliation_type` 为内部字段，用于区分来源文件，前端可忽略。

---

## 3. 获取 Session 信息

### 请求

```
GET /api/data/session-info
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |

### 响应

```json
{
  "session_id": "6e9c9d5011f946498cbb237ed364821d",
  "file_type": "affiliation",
  "record_count": 244,
  "parsed_fields": {
    "affiliation_country": {
      "total": 245,
      "parsed": 0
    },
    "affiliation_org": {
      "total": 0,
      "parsed": 0
    },
    "affiliation_city": {
      "total": 0,
      "parsed": 0
    }
  }
}
```

### 字段说明

- `parsed_fields`：三个子类型的解析进度，`total` 为总数，`parsed` 为已解析出经纬度的数量
- 当前上传场景中只有 `affiliation_country` 和 `affiliation_org` 有数据，`affiliation_city` 固定为空

---

## 4. AI 解析

一次性解析所有子类型（国家 / 机构），三种同步进行。

### 请求

```
POST /api/geo/parse-affiliation
Content-Type: application/json
```

### Body

```json
{
  "session_id": "6e9c9d5011f946498cbb237ed364821d",
  "ai_configs": [
    {
      "type": "official",
      "provider": "OpenAI",
      "api_key": "sk-...",
      "model": "gpt-4o-mini",
      "name": ""
    }
  ],
  "batch_size": 30
}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |
| `ai_configs` | array | ✅ | AI 模型配置列表，支持多模型并行 |
| `batch_size` | int | ❌ | 批处理大小，默认 30 |

### AI Config 详细字段

```json
{
  "type": "official",           // "official"（官方 API）或 "local"（本地模型）
  "provider": "OpenAI",         // 提供商名称，如 OpenAI / Azure / Custom
  "api_key": "sk-...",          // API Key（local 类型可为空）
  "base_url": "",               // 自定义 base URL（可选）
  "model": "gpt-4o-mini",       // 模型名称
  "name": ""                    // 显示名称（可选）
}
```

### 响应

```json
{
  "message": "解析任务已启动",
  "session_id": "6e9c9d5011f946498cbb237ed364821d"
}
```

---

## 5. 查询解析进度

轮询此接口获取实时进度。

### 请求

```
GET /api/geo/parse-progress
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |

### 响应

```json
{
  "overall_status": "running",
  "overall_progress": 33,
  "logs": [
    "启动 affiliation 全量解析 | 244 条记录 | 1 个模型",
    "模型: OpenAI:gpt-4o-mini"
  ],
  "tiers": {
    "affiliation_country": {
      "status": "running",
      "progress": 45,
      "logs": [
        "[国家] 启动 | 共 5 个唯一名称 | 1 个模型 | 超时 2.0s/次",
        "[国家] 阶段 1：主轮多模型快速解析",
        "  ✓ [OpenAI:gpt-4o-mini] CHINA",
        "  ✓ [OpenAI:gpt-4o-mini] USA"
      ]
    },
    "affiliation_org": {
      "status": "running",
      "progress": 20,
      "logs": [
        "[机构] 启动 | 共 100 个唯一名称 | 1 个模型 | 超时 2.0s/次"
      ]
    },
    "affiliation_city": {
      "status": "done",
      "progress": 100,
      "logs": [
        "[affiliation_city] 无数据，跳过"
      ]
    }
  }
}
```

### 状态值说明

| 值 | 说明 |
|---|---|
| `running` | 解析中 |
| `done` | 解析完成 |
| `stopped` | 已停止 |
| `stopping` | 正在停止 |
| `error` | 出错 |

### 前端轮询建议

- 轮询间隔：`1~2 秒`
- 结束条件：`overall_status === "done"` 或 `"stopped"` 或 `"error"`

---

## 6. 停止解析

### 请求

```
POST /api/geo/stop-parse
Content-Type: application/x-www-form-urlencoded
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |

### 响应

```json
{
  "message": "已向所有层级发送停止信号"
}
```

---

## 7. 查询解析结果

**返回格式与 C1 完全一致**，前端可直接复用 C1 的表格渲染逻辑。

### 请求

```
GET /api/geo/results
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |
| `field` | string | ✅ | 子类型字段名（见下方列表） |
| `page` | int | ❌ | 页码，默认 1 |
| `page_size` | int | ❌ | 每页条数，默认 50 |

### field 可选值

| field 值 | 说明 | 对应 name 列 |
|---|---|---|
| `affiliation_country` | 国家结果 | `Country/Region` |
| `affiliation_org` | 机构结果 | `Organization` |
| `affiliation_city` | 城市结果 | `City1` |

### 响应

```json
{
  "total": 5,
  "page": 1,
  "page_size": 50,
  "records": [
    {
      "Country/Region": "CHINA",
      "Organization": "",
      "City1": "",
      "City2": "",
      "Latitude": 35.8617,
      "Longitude": 104.1954,
      "ParseSrc": "ai",
      "ParseModel": "OpenAI:gpt-4o-mini"
    },
    {
      "Country/Region": "USA",
      "Organization": "",
      "City1": "",
      "City2": "",
      "Latitude": 37.0902,
      "Longitude": -95.7129,
      "ParseSrc": "ai",
      "ParseModel": "OpenAI:gpt-4o-mini"
    }
  ],
  "empty_count": 0
}
```

### 字段说明

| 字段 | 说明 |
|---|---|
| `Country/Region` | 国家名称（仅 affiliation_country 类型有值） |
| `Organization` | 机构名称（仅 affiliation_org 类型有值） |
| `City1` | 城市名称（仅 affiliation_city 类型有值） |
| `Latitude` | 纬度 |
| `Longitude` | 经度 |
| `ParseSrc` | 解析来源：`ai`（AI 解析）/ `rule`（规则解析）/ `pending`（待解析） |
| `ParseModel` | 使用的模型名称 |
| `empty_count` | 经纬度为空或无效的记录数 |

---

## 8. 获取可视化数据

**返回格式与 C1 完全一致**，前端可直接复用地图散点图的渲染逻辑。

### 请求

```
GET /api/geo/viz-data
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 上传返回的 session_id |
| `field` | string | ✅ | 子类型字段名（见下方列表） |
| `top_n` | int | ❌ | 排名数量，默认 30 |

### field 可选值（与 results 接口一致）

| field 值 | 说明 |
|---|---|
| `affiliation_country` | 国家地图数据 |
| `affiliation_org` | 机构地图数据 |
| `affiliation_city` | 城市地图数据 |

### 响应

```json
{
  "field": "affiliation_country",
  "parsed": true,
  "parse_stats": {
    "total": 5,
    "parsed": 5,
    "percent": 100,
    "complete": true
  },
  "country_counts": [
    {"Name": "CHINA", "value": 5511},
    {"Name": "USA", "value": 3002}
  ],
  "org_counts": [],
  "city_counts": [],
  "geocode_items": [
    {
      "country": "CHINA",
      "org": "",
      "city": "",
      "lat": 35.8617,
      "lng": 104.1954,
      "count": 5511
    },
    {
      "country": "USA",
      "org": "",
      "city": "",
      "lat": 37.0902,
      "lng": -95.7129,
      "count": 3002
    }
  ]
}
```

### 字段说明

| 字段 | 说明 |
|---|---|
| `parse_stats.total` | 总记录数 |
| `parse_stats.parsed` | 已解析出有效经纬度的记录数 |
| `parse_stats.percent` | 解析完成百分比 |
| `parse_stats.complete` | 是否全部完成 |
| `country_counts` | 国家排名列表（仅 affiliation_country 时有数据） |
| `org_counts` | 机构排名列表（仅 affiliation_org 时有数据） |
| `city_counts` | 城市排名列表（仅 affiliation_city 时有数据） |
| `geocode_items` | 地图散点数据，与 C1 格式完全一致 |

---

## 9. 清除 Session

### 请求

```
DELETE /api/data/session/{session_id}
```

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | ✅ | 要清除的 session_id |

### 响应

```json
{
  "message": "Session 已清除",
  "session_id": "6e9c9d5011f946498cbb237ed364821d"
}
```

---

## 完整前端调用流程

```
① 上传文件（一次三个）
   POST /api/data/upload
   → 拿到 session_id

② 查询原始数据（可选，用于预览上传结果）
   GET /api/data/records?session_id=xxx

③ 发起 AI 解析
   POST /api/geo/parse-affiliation
   → {"message": "解析任务已启动"}

④ 轮询解析进度
   GET /api/geo/parse-progress?session_id=xxx
   → overall_status === "done" 时结束轮询

⑤ 查询解析结果（国家）
   GET /api/geo/results?session_id=xxx&field=affiliation_country
   → 渲染国家表格

⑥ 查询可视化数据（国家）
   GET /api/geo/viz-data?session_id=xxx&field=affiliation_country
   → 渲染国家地图

⑦ 查询解析结果（机构）[同上，field 换为 affiliation_org]
   GET /api/geo/results?session_id=xxx&field=affiliation_org
   GET /api/geo/viz-data?session_id=xxx&field=affiliation_org
```

### 与 C1 的主要区别

| 对比项 | C1 / WoS 类型 | Affiliation 类型 |
|---|---|---|
| 上传文件数 | 单个 WoS/BP 文件 | 一次三个文件 |
| 解析字段 | 从 C1 字段解析 | 从文件 name 列解析 |
| field 参数 | `C1` / `C3` | `affiliation_country` / `affiliation_org` / `affiliation_city` |
| 返回格式 | 完全一致 | 完全一致 |
| 表格渲染 | 完全一致 | 完全一致 |
| 地图渲染 | 完全一致 | 完全一致 |
