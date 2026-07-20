# AiGeovis API 文档

> 基于 FastAPI 构建的地理编码与数据解析 API。版本：1.2.0

---

## 概述

本 API 支持两种数据格式的文件上传与解析：

| 类型                 | `file_type`   | 说明                             | 上传后操作                     |
| -------------------- | ------------- | -------------------------------- | ------------------------------ |
| **WoS/BP 格式**      | `wos`         | 多行文献记录，含 C1/C3 地址字段  | 用户选择 C1/C3 后手动触发解析  |
| **Affiliation 格式** | `affiliation` | TSV 文件，含机构/国家名称 + 数量 | 直接触发 AI 解析，无需选择字段 |

前端上传后通过返回的 `file_type` 字段判断文件类型：

- `file_type === "affiliation"`：隐藏 C1/C3 选择，直接调用 `/api/geo/parse-affiliation`
- `file_type === "wos"`：原有逻辑不变

---

## 通用说明

- 所有 POST 请求除非注明 `Content-Type: multipart/form-data`，均使用 `application/json`
- 所有接口基础地址：`http://localhost:8000`
- `session_id` 由上传接口返回，用于后续所有请求的身份标识
- 解析任务均为**后台异步执行**，前端需轮询 `/api/geo/parse-progress` 获取进度

---

## 1. 健康检查

```
GET /api/health
```

检查服务是否正常运行。

**响应示例：**

```json
{
  "status": "ok",
  "version": "1.2.0"
}
```

---

## 2. 上传数据文件

```
POST /api/data/upload
Content-Type: multipart/form-data
```

统一上传入口，根据文件内容自动识别格式类型。

**请求参数：**

| 参数    | 类型 | 必填 | 说明                             |
| ------- | ---- | ---- | -------------------------------- |
| `files` | file | 是   | 上传文件，支持多文件（自动合并） |

**支持的文件格式：**

- **WoS/BP**：`.txt` 文献记录文件（默认）
- **Affiliation**：`.txt` TSV 文件（自动检测首行列名）

**响应示例：**

```json
// WoS/BP 格式
{
  "session_id": "a1b2c3d4e5f6",
  "record_count": 1500,
  "columns": ["TI", "AU", "C1", "C3", "PY", ...],
  "files": ["record.txt"],
  "file_type": "wos"
}

// Affiliation 格式
{
  "session_id": "f6e5d4c3b2a1",
  "record_count": 68295119,
  "columns": ["name", "count"],
  "files": ["Affiliations.txt"],
  "file_type": "affiliation"
}
```

**响应字段说明：**

| 字段           | 类型    | 说明                                 |
| -------------- | ------- | ------------------------------------ |
| `session_id`   | string  | 会话标识，后续所有接口必传           |
| `record_count` | integer | 解析出的记录数量                     |
| `columns`      | array   | 数据列名列表                         |
| `files`        | array   | 上传的文件名列表                     |
| `file_type`    | string  | 文件类型：`"wos"` 或 `"affiliation"` |

---

## 3. 获取 Session 信息

```
GET /api/data/session-info
```

获取当前 session 的状态和解析进度。

**请求参数：**

| 参数         | 类型   | 必填 | 说明                      |
| ------------ | ------ | ---- | ------------------------- |
| `session_id` | string | 是   | 上传接口返回的 session_id |

**响应示例：**

```json
// WoS/BP 类型
{
  "session_id": "a1b2c3d4e5f6",
  "file_type": "wos",
  "record_count": 1500,
  "parsed_fields": {
    "C1": {"total": 1200, "parsed": 800},
    "C3": {"total": 500, "parsed": 0}
  }
}

// Affiliation 类型
{
  "session_id": "f6e5d4c3b2a1",
  "file_type": "affiliation",
  "record_count": 68295119,
  "parsed_fields": {
    "affiliation": {"total": 68295119, "parsed": 0}
  }
}
```

---

## 4. 解析 Affiliation 文件（新增）

```
POST /api/geo/parse-affiliation
Content-Type: application/json
```

**仅限 `file_type=affiliation` 的 session 调用。**

将机构/国家名称批量发送给 AI，解析出国家、城市、经纬度。解析完成后结果存入 `session["parsed_df_affiliation"]`，前端可直接调用 `/api/geo/viz-data` 获取可视化数据。

**请求体：**

```json
{
  "session_id": "f6e5d4c3b2a1",
  "ai_configs": [
    {
      "type": "official",
      "provider": "OpenAI",
      "api_key": "sk-xxxxx",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-4o-mini",
      "name": "GPT-4o-mini"
    }
  ],
  "batch_size": 20
}
```

**请求字段说明：**

| 字段         | 类型    | 必填 | 说明                            |
| ------------ | ------- | ---- | ------------------------------- |
| `session_id` | string  | 是   | 上传接口返回的 session_id       |
| `ai_configs` | array   | 是   | AI 模型配置列表，支持多模型并行 |
| `batch_size` | integer | 否   | 每轮并发请求数，默认 20         |

**AIConfig 字段说明：**

| 字段       | 类型   | 默认值          | 说明                                         |
| ---------- | ------ | --------------- | -------------------------------------------- |
| `type`     | string | `"official"`    | `"official"` 或 `"local"`（Ollama）          |
| `provider` | string | `"OpenAI"`      | 模型提供商：`OpenAI` / `Gemini` / `Custom`   |
| `api_key`  | string | `""`            | API Key，local 类型可为空                    |
| `base_url` | string | `""`            | API 基础地址，如 `https://api.openai.com/v1` |
| `model`    | string | `"gpt-4o-mini"` | 模型名称                                     |
| `name`     | string | `""`            | 显示名称（可选）                             |

**响应示例：**

```json
{
  "message": "解析任务已启动",
  "session_id": "f6e5d4c3b2a1"
}
```

> 注意：此接口为**异步后台任务**，返回即表示任务已启动。前端需轮询 `/api/geo/parse-progress` 获取实时进度。

---

## 5. 解析 C1 地址（WoS）

```
POST /api/geo/parse-c1
Content-Type: application/json
```

**仅限 `file_type=wos` 的 session 调用。**

解析 WoS/BP 数据中的 C1（或 C3）地址字段，将地址批量发送给 AI，提取国家、城市、机构、经纬度。

**请求体：**

```json
{
  "session_id": "a1b2c3d4e5f6",
  "ai_configs": [
    {
      "type": "official",
      "provider": "OpenAI",
      "api_key": "sk-xxxxx",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-4o-mini",
      "name": "GPT-4o-mini"
    }
  ],
  "batch_size": 30,
  "field": "C1"
}
```

**响应示例：**

```json
{
  "message": "C1 解析任务已启动",
  "session_id": "a1b2c3d4e5f6",
  "field": "C1"
}
```

---

## 6. 批量分层解析（WoS）

```
POST /api/geo/parse-batch-tiers
Content-Type: application/json
```

**仅限 `file_type=wos` 的 session 调用。**

同时解析国家、城市、机构多个层级，并行执行。

**请求体：**

```json
{
  "session_id": "a1b2c3d4e5f6",
  "ai_configs": [
    {
      "type": "official",
      "provider": "OpenAI",
      "api_key": "sk-xxxxx",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-4o-mini",
      "name": "GPT-4o-mini"
    }
  ],
  "batch_size": 30,
  "field": "C1",
  "tiers": ["country", "city", "org"]
}
```

`tiers` 数组可选值：`"country"` / `"city"` / `"org"`，可任意组合。

---

## 7. 查询解析进度

```
GET /api/geo/parse-progress
```

轮询获取当前解析任务的实时进度。

**请求参数：**

| 参数         | 类型   | 必填 | 说明       |
| ------------ | ------ | ---- | ---------- |
| `session_id` | string | 是   | session_id |

**响应示例：**

```json
// Affiliation 解析
{
  "status": "running",
  "progress": 45,
  "logs": [
    "启动 affiliation 解析，共 68295119 条记录，使用 1 个模型...",
    "═══ 阶段 1：主轮多模型快速解析 ═══",
    "── 第 1 轮：处理 100000 个名称 ──",
    "   第 1 轮完成：成功 98500，待重试 1500，累计 98500/68295119"
  ]
}

// 批量分层解析（WoS）
{
  "overall_status": "running",
  "overall_progress": 60,
  "tiers": {
    "country": {"status": "done", "progress": 100, "logs": ["✅ 全部完成！..."]},
    "city":    {"status": "running", "progress": 75, "logs": ["── 第 2 轮..."]},
    "org":     {"status": "running", "progress": 45, "logs": ["── 第 1 轮..."]}
  }
}
```

**`status` 状态值：**

| 值         | 说明     |
| ---------- | -------- |
| `running`  | 解析中   |
| `done`     | 解析完成 |
| `stopped`  | 用户停止 |
| `stopping` | 正在停止 |
| `error`    | 出错     |

---

## 8. 停止解析

```
POST /api/geo/stop-parse
```

**请求参数：**

| 参数         | 类型   | 必填 | 说明       |
| ------------ | ------ | ---- | ---------- |
| `session_id` | string | 是   | session_id |

**响应示例：**

```json
{
  "message": "停止信号已发送"
}
```

---

## 9. 获取可视化数据

```
GET /api/geo/viz-data
```

获取用于地图可视化和统计图表的聚合数据，是前端地图绑定的核心数据源。

**请求参数：**

| 参数         | 类型    | 默认值 | 说明                                           |
| ------------ | ------- | ------ | ---------------------------------------------- |
| `session_id` | string  | 必填   | session_id                                     |
| `field`      | string  | `"C1"` | WoS 类型：字段名；Affiliation 类型：忽略此参数 |
| `top_n`      | integer | `30`   | 排名列表返回的最大数量                         |

**响应示例：**

```json
{
  "field": "affiliation",
  "parsed": true,
  "parse_stats": {
    "total": 68295119,
    "parsed": 68295119,
    "percent": 100,
    "complete": true
  },
  "country_counts": [
    { "name": "China", "value": 18500000 },
    { "name": "United States", "value": 12000000 },
    { "name": "Germany", "value": 3100000 }
  ],
  "org_counts": [
    { "name": "Chinese Academy Of Sciences", "value": 850000 },
    { "name": "Harvard University", "value": 320000 }
  ],
  "city_counts": [
    { "name": "Beijing", "value": 5200000 },
    { "name": "New York", "value": 2100000 }
  ],
  "geocode_items": [
    {
      "country": "China",
      "organization": "Chinese Academy Of Sciences",
      "city": "Beijing",
      "lat": 39.9042,
      "lng": 116.4074,
      "count": 850000
    }
  ]
}
```

---

## 10. 获取解析结果（分页）

```
GET /api/geo/results
```

分页获取解析结果列表，包含完整的国家、城市、经纬度等字段。未完整解析的记录排在前面。

**请求参数：**

| 参数         | 类型    | 默认值 | 说明                                             |
| ------------ | ------- | ------ | ------------------------------------------------ |
| `session_id` | string  | 必填   | session_id                                       |
| `page`       | integer | `1`    | 页码                                             |
| `page_size`  | integer | `50`   | 每页条数                                         |
| `field`      | string  | `"C1"` | WoS 类型：C1 或 C3；Affiliation 类型：忽略此参数 |

**响应示例（Affiliation）：**

```json
{
  "total": 68295119,
  "page": 1,
  "page_size": 50,
  "empty_count": 120,
  "records": [
    {
      "Name": "Chinese Academy Of Sciences",
      "Count": 850000,
      "Country": "China",
      "City": "Beijing",
      "Latitude": 39.9042,
      "Longitude": 116.4074,
      "ParseSrc": "ai",
      "ParseModel": "GPT-4o-mini"
    }
  ]
}
```

---

## 11. 分层统计（WoS）

```
GET /api/geo/stats
```

分层统计接口，按国家/城市/机构独立聚合，各自带坐标和数量。

**请求参数：**

| 参数         | 类型    | 默认值      | 说明                             |
| ------------ | ------- | ----------- | -------------------------------- |
| `session_id` | string  | 必填        | session_id                       |
| `field`      | string  | `"C1"`      | 字段名                           |
| `tier`       | string  | `"country"` | 层级：`country` / `city` / `org` |
| `top_n`      | integer | `30`        | 返回条数                         |

---

## 12. 地理编码

```
POST /api/geo/geocode
Content-Type: application/json
```

将已解析的国家/城市/机构信息通过高德地图或 Nominatim 获取精确经纬度。

**请求体：**

```json
{
  "session_id": "a1b2c3d4e5f6",
  "amap_key": "your-amap-key",
  "use_nominatim": true,
  "field": "C1"
}
```

---

## 13. 列出可用模型

```
POST /api/models/list
Content-Type: application/json
```

查询指定 API 端点支持的模型列表。

**请求体：**

```json
{
  "type": "official",
  "provider": "OpenAI",
  "api_key": "sk-xxxxx",
  "base_url": "https://api.openai.com/v1"
}
```

---

## 15. 模型基准测试

```
POST /api/models/benchmark
Content-Type: application/json
```

并发测试所有可用模型的真实解析速度，按响应时间升序返回。

---

## 16. 导出实体矩阵为 GML 文件

```
GET /api/geo/entity-matrix/export
```

将 entity-matrix 数据导出为 GML（Gephi Graph Modeling Language）格式，可导入 Gephi、VOSviewer 等网络分析工具。

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|-----|------|------|--------|------|
| `session_id` | string | 是 | - | 会话ID |
| `field` | string | 否 | `"C1"` | 字段：`C1` / `C3` |
| `tier` | string | 否 | `"country"` | 层级：`country` / `city` / `org` |
| `top_n` | integer | 否 | `50` | 高频实体数量 |
| `threshold` | integer | 否 | `0` | 边权重阈值 |
| `coord_type` | string | 否 | `"normalized"` | 坐标类型 |
| `include_matrix` | boolean | 否 | `false` | 包含邻接矩阵 |

**`coord_type` 可选值：**

| 值 | 说明 | 适用场景 |
|---|------|---------|
| `normalized` | 标准化到 `[-1, 1]` 范围 | 网络可视化（Gephi/VOSviewer） |
| `geo` | 直接使用经纬度（lng, lat） | 地理可视化 / GIS软件 |
| `none` | 不输出 x, y 坐标 | 纯关系图，无需布局 |

**响应：** 文件流（`.gml` 文件）

**请求示例：**

```http
GET /api/geo/entity-matrix/export?session_id=xxx&tier=city&coord_type=normalized
```

```http
GET /api/geo/entity-matrix/export?session_id=xxx&tier=org&coord_type=geo&include_matrix=true
```

**返回的 GML 文件示例：**

```gml
Creator "AiGeovis Entity Matrix Exporter"
graph
[
  directed 0

  node
  [
    id 0
    label "China"
    x 0.234500
    y 0.678900
    weight<frequency> 1280
    weight<links> 15
    weight<total_link_strength> 245
  ]

  node
  [
    id 1
    label "United States"
    x -0.123400
    y 0.456700
    weight<frequency> 960
    weight<links> 12
    weight<total_link_strength> 180
  ]

  edge
  [
    source 0
    target 1
    value 45.0
  ]
]
```

**节点属性说明：**

| GML 属性 | 来源 | 说明 |
|---------|------|------|
| `id` | 自动生成 | 0, 1, 2, ... |
| `label` | `nodes[i].name` | 实体名称 |
| `x` | 坐标转换 | 见 coord_type 说明 |
| `y` | 坐标转换 | 见 coord_type 说明 |
| `weight<frequency>` | `nodes[i].frequency` | 实体出现频次 |
| `weight<links>` | 计算得出 | 该实体连接的边数 |
| `weight<total_link_strength>` | 计算得出 | 所有边的权重之和 |
| `geo<lat>` | `nodes[i].lat` | 仅 `coord_type=geo` 时输出 |
| `geo<lng>` | `nodes[i].lng` | 仅 `coord_type=geo` 时输出 |

---

## 17. 其他数据接口

| 方法      | 路径                          | 说明                       |
| -------- | --------------------------- | -------------------------- |
| `GET`    | `/api/data/records`         | 分页获取原始数据记录       |
| `GET`    | `/api/data/summary`         | 数据摘要统计（年份分布等） |
| `GET`    | `/api/data/export`          | 导出已解析数据为 Excel     |
| `DELETE` | `/api/data/session`         | 清除指定 session           |
| `DELETE` | `/api/data/sessions`        | 清除所有 session           |
| `GET`    | `/api/geo/tier-results`     | 获取分层解析结果           |
| `GET`    | `/api/geo/tier-progress`    | 查询分层解析进度           |
| `GET`    | `/api/demo/files`           | 获取演示数据文件列表       |
| `GET`    | `/api/demo/data/{filename}` | 获取演示数据内容           |

---

## 数据流总览

### Affiliation 类型（新增）

```
上传文件
  → /api/data/upload (file_type=affiliation)
  → 返回 session_id
  → /api/geo/parse-affiliation (后台异步)
  → 轮询 /api/geo/parse-progress
  → 解析完成
  → /api/geo/viz-data (直接获取可视化数据)
  → /api/geo/results (获取结果列表)
```

### WoS/BP 类型

```
上传文件
  → /api/data/upload (file_type=wos)
  → 返回 session_id + columns
  → 用户选择 C1 或 C3
  → /api/geo/parse-c1 或 /api/geo/parse-batch-tiers
  → 轮询 /api/geo/parse-progress
  → 解析完成
  → /api/geo/viz-data
  → /api/geo/results
  → /api/geo/geocode (可选，补经纬度)
```
