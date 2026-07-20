# Entity Matrix GML 导出接口文档

## 概述

`/api/geo/entity-matrix/export` 接口用于将 entity-matrix 数据导出为 **GML（Gephi Graph Modeling Language）** 格式，可直接导入 Gephi、VOSviewer 等网络分析工具进行可视化分析。

---

## 接口信息

| 属性 | 值 |
|------|-----|
| **方法** | `GET` |
| **路径** | `/api/geo/entity-matrix/export` |
| **返回类型** | 文件流（`.gml`） |
| **字符编码** | UTF-8 |

---

## 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `session_id` | string | 是 | - | 会话ID（从数据上传接口获取） |
| `field` | string | 否 | `"C1"` | 字段类型：`C1` 或 `C3` |
| `tier` | string | 否 | `"country"` | 分析层级：`country` / `city` / `org` |
| `top_n` | integer | 否 | `50` | 导出节点数量上限 |
| `threshold` | integer | 否 | `0` | 边权重阈值，低于此值的边不导出 |
| `coord_type` | string | 否 | `"normalized"` | 坐标类型（见下方说明） |
| `include_matrix` | boolean | 否 | `false` | 是否在文件中包含邻接矩阵 |

---

## coord_type 参数说明

| 值 | 说明 | 适用场景 |
|---|------|---------|
| `normalized` | 坐标标准化到 `[-1, 1]` 范围 | Gephi / VOSviewer 网络布局 |
| `geo` | 直接使用经纬度（lng, lat） | GIS 软件 / 地理可视化 |
| `none` | 不输出 x, y 坐标 | 纯关系图，无需预设布局 |

### coord_type=normalized 示例

```gml
node
[
  id 0
  label "China"
  x 0.789856
  y -1.000000
]
```

### coord_type=geo 示例

```gml
node
[
  id 0
  label "China"
  x 104.195400    // longitude
  y 35.861700     // latitude
  geo<lat> 35.861700
  geo<lng> 104.195400
]
```

---

## 请求示例

### 基础用法（标准化坐标，适合 Gephi）

```http
GET /api/geo/entity-matrix/export?session_id=abc123&tier=country
```

### 指定节点数量和阈值

```http
GET /api/geo/entity-matrix/export?session_id=abc123&tier=city&top_n=30&threshold=5
```

### 导出地理坐标（适合 GIS）

```http
GET /api/geo/entity-matrix/export?session_id=abc123&tier=country&coord_type=geo
```

### 包含邻接矩阵（用于高级分析）

```http
GET /api/geo/entity-matrix/export?session_id=abc123&tier=org&include_matrix=true
```

### 完整参数示例

```http
GET /api/geo/entity-matrix/export?session_id=abc123&field=C1&tier=city&top_n=20&threshold=3&coord_type=normalized&include_matrix=true
```

---

## GML 文件格式说明

### 文件结构

```gml
Creator "AiGeovis Entity Matrix Exporter"
graph
[
  directed 0

  node
  [
    id 0
    label "China"
    x 0.789856
    y -1.000000
    weight<frequency> 437
    weight<links> 9
    weight<total_link_strength> 164
  ]
  ...

  edge
  [
    source 0
    target 1
    value 68.0
  ]
  ...

  /* Co-occurrence Matrix */
  /*
  matrix_dim 10
  matrix_labels ["China", "United States", ...]
  matrix_values [
    [437, 68, ...],
    [68, 251, ...],
    ...
  ]
  */
]
```

### 节点属性

| GML 属性 | 数据来源 | 说明 |
|---------|---------|------|
| `id` | 自动生成 | 节点索引，从 0 开始 |
| `label` | `nodes[i].name` | 实体名称（如国家/城市/机构名） |
| `x` | 坐标转换 | 横坐标，见 coord_type 说明 |
| `y` | 坐标转换 | 纵坐标，见 coord_type 说明 |
| `weight<frequency>` | `nodes[i].frequency` | 实体出现的文献频次 |
| `weight<links>` | 计算得出 | 该实体连接的边数量 |
| `weight<total_link_strength>` | 计算得出 | 所有边权重之和 |
| `geo<lat>` | `nodes[i].lat` | 纬度，仅 `coord_type=geo` 时输出 |
| `geo<lng>` | `nodes[i].lng` | 经度，仅 `coord_type=geo` 时输出 |

### 边属性

| GML 属性 | 数据来源 | 说明 |
|---------|---------|------|
| `source` | 节点ID | 边起点 |
| `target` | 节点ID | 边终点 |
| `value` | `edges[i].weight` | 共现权重/次数 |

---

## 完整 GML 示例文件

```gml
Creator "AiGeovis Entity Matrix Exporter"
graph
[
  directed 0

  node
  [
    id 0
    label "China"
    x 0.789856
    y -1.000000
    weight<frequency> 437
    weight<links> 9
    weight<total_link_strength> 164
  ]

  node
  [
    id 1
    label "United States"
    x -1.000000
    y -0.595878
    weight<frequency> 251
    weight<links> 9
    weight<total_link_strength> 147
  ]

  edge
  [
    source 0
    target 1
    value 68.0
  ]
]
```

---

## 前端调用示例

### 方法一：直接跳转下载

```javascript
// 直接下载文件
window.location.href = '/api/geo/entity-matrix/export?session_id=xxx&tier=city';
```

### 方法二：Ajax 下载（推荐）

```javascript
async function downloadGML(sessionId, tier = 'country', options = {}) {
  const params = new URLSearchParams({
    session_id: sessionId,
    tier: tier,
    ...options
  });

  const response = await fetch(`/api/geo/entity-matrix/export?${params}`);
  const blob = await response.blob();

  // 创建下载链接
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `entity_matrix_${tier}_${Date.now()}.gml`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// 调用示例
downloadGML('abc123', 'country', {
  coord_type: 'normalized',
  top_n: 30,
  include_matrix: true
});
```

### 方法三：使用 Element Plus 或其他 UI 框架

```javascript
import { ElMessage } from 'element-plus';

async function downloadGML() {
  try {
    ElMessage.info('正在生成 GML 文件...');

    const response = await fetch('/api/geo/entity-matrix/export?session_id=xxx');
    const blob = await response.blob();

    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'entity_matrix.gml';
    link.click();

    URL.revokeObjectURL(url);
    ElMessage.success('下载完成');
  } catch (error) {
    ElMessage.error('下载失败: ' + error.message);
  }
}
```

---

## 错误响应

### 400 Bad Request - 参数错误

```json
{
  "detail": "tier 必须是 country / city / org 之一"
}
```

### 400 Bad Request - 数据未解析

```json
{
  "detail": "该 session 尚未解析 field=C1 tier=country 的数据，请先调用 /api/geo/parse-tier 解析 country 层"
}
```

### 404 Not Found - Session 不存在

```json
{
  "detail": "Session 不存在"
}
```

---

## 典型工作流程

```
1. 上传数据文件
   POST /api/data/upload
   → 返回 session_id

2. 解析数据（根据需要）
   GET /api/geo/parse-tier?session_id=xxx&field=C1&tier=country

3. 导出 GML
   GET /api/geo/entity-matrix/export?session_id=xxx&tier=country

4. 在 Gephi/VOSviewer 中打开 GML 文件
```

---

## 在 Gephi 中使用

1. 打开 Gephi
2. 文件 → 打开 → 选择 `.gml` 文件
3. 选择布局算法（如 ForceAtlas、Geo Layout）
4. 调整节点大小（按 frequency）
5. 调整边的粗细（按 value）
6. 导出为 PNG/SVG

### Gephi 布局建议

| coord_type | 推荐布局 |
|------------|---------|
| `normalized` | ForceAtlas 2 / Yifan Hu |
| `geo` | Geo Layout（需要启用地图插件） |
| `none` | ForceAtlas 2 / Circular |

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-06-11 | 初始版本 |
