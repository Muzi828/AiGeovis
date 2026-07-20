# Entity Matrix API 文档（前端对接版）

> 适用接口：`GET /api/geo/entity-matrix`
>
> 本文档面向前端，说明 `org / city / country` 共现矩阵接口的请求方式、返回字段含义，以及推荐渲染方式。

---

## 1. 接口概述

该接口用于从已解析完成的 `C1` 或 `C3` 数据中，按“文献”为统计单元构建实体共现矩阵。

支持三种分析层级：

- `country`：国家共现矩阵
- `city`：城市共现矩阵
- `org`：机构共现矩阵

对于当前前端要接的这个请求：

```text
http://localhost:8000/api/geo/entity-matrix?session_id=a302e588567e4d4c9f9fa378a565062d&field=C1&tier=org&top_n=20&threshold=0
```

它的含义是：

- 使用当前 `session_id` 对应的数据集
- 基于 `C1` 字段
- 以 `org`（机构）为分析层级
- 取出现频次最高的前 `20` 个机构进入矩阵
- 返回所有边（`threshold=0`）

---

## 2. 统计口径

### 2.1 基本统计单元

矩阵按“文献”统计，不按“地址条目”统计。

也就是说：

- 同一篇论文里同一个机构出现多次，只记一次
- 两个机构只要在同一篇论文中共同出现，该机构对的共现次数加 `1`

### 2.2 `org / city` 层级的实体名称规则

在 `org` 和 `city` 层级下，返回的实体名称就是实体本身，不再拼接国家前缀。

例如：

```text
Chinese Academy of Sciences
Harvard University
Beijing
Cambridge
```

### 2.3 矩阵含义

假设矩阵中的实体顺序为：

```text
[
  "Chinese Academy of Sciences",
  "Harvard University",
  "University of Oxford"
]
```

则：

- `matrix[i][i]`：第 `i` 个机构出现在多少篇论文中
- `matrix[i][j]`：第 `i` 个机构与第 `j` 个机构共同出现在多少篇论文中
- 矩阵是对称矩阵，即 `matrix[i][j] === matrix[j][i]`

---

## 3. 请求信息

### 3.1 请求方式

```text
GET /api/geo/entity-matrix
```

### 3.2 Base URL

```text
http://localhost:8000
```

### 3.3 请求参数

| 参数         | 类型    | 必填 | 示例                               | 说明                                                      |
| ------------ | ------- | ---- | ---------------------------------- | --------------------------------------------------------- |
| `session_id` | string  | 是   | `a302e588567e4d4c9f9fa378a565062d` | 上传数据后返回的会话 ID                                   |
| `field`      | string  | 否   | `C1`                               | 分析字段，支持 `C1` / `C3`，默认 `C1`                     |
| `tier`       | string  | 否   | `org`                              | 分析层级，支持 `country` / `city` / `org`，默认 `country` |
| `top_n`      | integer | 否   | `20`                               | 参与矩阵计算的高频实体数量，默认 `50`                     |
| `threshold`  | integer | 否   | `0`                                | 边的最小权重阈值，默认 `0`                                |

### 3.4 当前接口请求示例

```http
GET http://localhost:8000/api/geo/entity-matrix?session_id=a302e588567e4d4c9f9fa378a565062d&field=C1&tier=org&top_n=20&threshold=0
```

### 3.6 `C3` 调用说明

当 `field=C3` 时，`entity-matrix` 读取的是 `C3` 的统一解析结果，而不是分层解析结果。

也就是说：

- `C1`：依赖 `country / city / org` 对应的分层解析结果
- `C3`：依赖一次性统一解析后的结果，再在矩阵阶段按 `tier` 抽取实体

示例：

```http
GET http://localhost:8000/api/geo/entity-matrix?session_id=fbadfe104a7c4ed6b57afe29cf7fc7de&field=C3&tier=org&top_n=20&threshold=0
```

推荐优先接入：

- `field=C3&tier=org`
- `field=C3&tier=country`

`field=C3&tier=city` 也支持，但结果质量依赖 `C3` 统一解析中的城市字段完整度。

## 4. 调用前置条件

调用该接口前，必须先保证：

1. 已经上传数据并获得 `session_id`
2. 当前 `session_id` 对应的数据里包含 `C1` 或 `C3`
3. 已完成对应字段所需的解析

前置条件按 `field` 区分：

- `field=C1`：必须先完成对应 `tier` 的分层解析
- `field=C3`：必须先完成 `C3` 的统一解析（即调用 `parse-c1` 且传 `field=C3`）

对于本次请求：

- `field=C1`
- `tier=org`

因此调用前必须已经完成 `C1` 的 `org` 层解析，否则接口会返回 `400`。

---

## 5. 返回结果结构

### 5.1 成功响应示例

```json
{
  "entities": [
    "China > Chinese Academy of Sciences",
    "United States > Harvard University",
    "United Kingdom > University of Oxford"
  ],
  "matrix": [
    [12, 4, 2],
    [4, 9, 3],
    [2, 3, 7]
  ],
  "nodes": [
    {
      "name": "China > Chinese Academy of Sciences",
      "frequency": 12,
      "lat": 39.9042,
      "lng": 116.4074
    },
    {
      "name": "United States > Harvard University",
      "frequency": 9,
      "lat": 42.377,
      "lng": -71.1167
    },
    {
      "name": "United Kingdom > University of Oxford",
      "frequency": 7,
      "lat": 51.752,
      "lng": -1.2577
    }
  ],
  "edges": [
    {
      "source": "China > Chinese Academy of Sciences",
      "target": "United States > Harvard University",
      "weight": 4
    },
    {
      "source": "China > Chinese Academy of Sciences",
      "target": "United Kingdom > University of Oxford",
      "weight": 2
    },
    {
      "source": "United States > Harvard University",
      "target": "United Kingdom > University of Oxford",
      "weight": 3
    }
  ],
  "total_papers": 128,
  "papers_with_entity": 96,
  "papers_without_entity": 32,
  "total_pairs": 54,
  "session_id": "a302e588567e4d4c9f9fa378a565062d",
  "field": "C1",
  "tier": "org"
}
```

> 说明：上面的数值仅为结构示例，实际值以接口返回为准。

---

## 6. 返回字段说明

### 6.1 顶层字段

| 字段                    | 类型       | 说明                                         |
| ----------------------- | ---------- | -------------------------------------------- |
| `entities`              | string[]   | 矩阵的行列标签列表，顺序与 `matrix` 完全一致 |
| `matrix`                | number[][] | 共现矩阵，大小为 `n x n`                     |
| `nodes`                 | object[]   | 实体节点列表，适合网络图、地图散点渲染       |
| `edges`                 | object[]   | 实体共现边列表，适合网络图、连线渲染         |
| `total_papers`          | number     | 当前 session 中参与聚合统计的总文献数        |
| `papers_with_entity`    | number     | 至少提取到一个该层级实体的文献数             |
| `papers_without_entity` | number     | 未提取到该层级实体的文献数                   |
| `total_pairs`           | number     | 所有有效共现边的累计权重总和                 |
| `session_id`            | string     | 当前会话 ID                                  |
| `field`                 | string     | 当前分析字段，`C1` 或 `C3`                   |
| `tier`                  | string     | 当前分析层级，`country` / `city` / `org`     |

### 6.2 `entities`

`entities` 是一个字符串数组，定义了矩阵的坐标轴顺序。

例如：

```json
[
  "China > Chinese Academy of Sciences",
  "United States > Harvard University",
  "United Kingdom > University of Oxford"
]
```

则对应关系为：

- `matrix[0][0]` 对应 `China > Chinese Academy of Sciences`
- `matrix[0][1]` 对应 `China > Chinese Academy of Sciences` 与 `United States > Harvard University`
- `matrix[2][2]` 对应 `United Kingdom > University of Oxford`

### 6.3 `matrix`

`matrix` 是二维数组，行列顺序和 `entities` 完全一致。

规则：

- 对角线 `matrix[i][i]`：该实体出现的文献数量
- 非对角线 `matrix[i][j]`：两个实体共同出现的文献数量
- 对称：`matrix[i][j] === matrix[j][i]`

示例：

```json
[
  [12, 4, 2],
  [4, 9, 3],
  [2, 3, 7]
]
```

含义：

- 第 1 个机构在 `12` 篇文献中出现
- 第 1 个机构与第 2 个机构共同出现在 `4` 篇文献中
- 第 2 个机构与第 3 个机构共同出现在 `3` 篇文献中

### 6.4 `nodes`

`nodes` 用于网络图节点或地图点位渲染。

每一项结构如下：

| 字段        | 类型           | 说明                                       |
| ----------- | -------------- | ------------------------------------------ |
| `name`      | string         | 实体名称，与 `entities` 中的值一致         |
| `frequency` | number         | 实体出现在多少篇文献中，可用于节点大小映射 |
| `lat`       | number \| null | 纬度，可能为空                             |
| `lng`       | number \| null | 经度，可能为空                             |

示例：

```json
{
  "name": "China > Chinese Academy of Sciences",
  "frequency": 12,
  "lat": 39.9042,
  "lng": 116.4074
}
```

### 6.5 `edges`

`edges` 用于网络图边渲染。

每一项结构如下：

| 字段     | 类型   | 说明                               |
| -------- | ------ | ---------------------------------- |
| `source` | string | 起点实体名称                       |
| `target` | string | 终点实体名称                       |
| `weight` | number | 共现权重，即共同出现在多少篇文献中 |

示例：

```json
{
  "source": "China > Chinese Academy of Sciences",
  "target": "United States > Harvard University",
  "weight": 4
}
```

### 6.6 统计字段

| 字段                    | 含义               | 前端用途建议           |
| ----------------------- | ------------------ | ---------------------- |
| `total_papers`          | 总文献数           | 页面概览统计           |
| `papers_with_entity`    | 有实体结果的文献数 | 展示解析覆盖率         |
| `papers_without_entity` | 无实体结果的文献数 | 异常提示或数据质量提示 |
| `total_pairs`           | 所有边权重总和     | 网络强度概览           |

---

## 7. 前端渲染方式建议

### 7.1 矩阵热力图 / 表格

推荐使用：

- `entities` 作为横轴和纵轴标签
- `matrix` 作为热力值来源

渲染规则：

- 对角线显示节点频次
- 非对角线显示共现强度
- 颜色深浅映射数值大小
- 如果实体较多，建议加横向滚动和 tooltip

推荐 tooltip 文案：

- 当 `i === j`：
  - `该机构出现在 X 篇文献中`
- 当 `i !== j`：
  - `两个机构共同出现在 X 篇文献中`

### 7.2 网络图

推荐直接使用：

- `nodes` 作为节点数据
- `edges` 作为边数据

推荐映射关系：

- `node.size = frequency`
- `edge.width = weight`
- `node.label = name`
- `edge.label` 可选显示 `weight`

建议：

- 当 `weight = 0` 时，前端可自行过滤，不渲染连边
- 当实体名称较长时，图上只显示截断标签，完整名称放在 tooltip 中

### 7.3 地图点位 / 飞线图

如果要做地图联动：

- 使用 `nodes[*].lat/lng` 作为点位坐标
- 使用 `edges` 结合 `source/target` 到 `nodes` 中查坐标
- 如果某个节点 `lat/lng` 为空，则跳过其地图绘制

推荐规则：

- 散点大小映射 `frequency`
- 飞线粗细映射 `weight`
- 点击节点时高亮与其有关的边

### 7.4 列表 / 统计卡片

顶部统计区建议直接使用：

- `total_papers`
- `papers_with_entity`
- `papers_without_entity`
- `total_pairs`

例如：

- 总文献数
- 有机构信息文献数
- 无机构信息文献数
- 总共现关系强度

---

## 8. 推荐前端数据处理

### 8.1 构建名称到节点的索引

在地图和网络图渲染时，建议前端先构建一个哈希表：

```js
const nodeMap = Object.fromEntries(data.nodes.map((node) => [node.name, node]));
```

这样可以方便根据 `edges[*].source` / `edges[*].target` 获取坐标和频次。

### 8.2 过滤无效边

当前接口在 `threshold=0` 时，可能会返回 `weight=0` 的边。

因此前端建议再做一次过滤：

```js
const validEdges = data.edges.filter((edge) => edge.weight > 0);
```

### 8.3 处理长标签

由于 `org` 层名称通常较长，例如：

```text
United States > University of California System
```

建议前端：

- 表格/热力图中支持 tooltip 展示完整名称
- 网络图中对 label 做截断显示
- 提供复制完整名称或 hover 全量展示

---

## 9. 错误响应说明

### 9.1 `400 Bad Request`：`tier` 非法

```json
{
  "detail": "tier 必须是 country / city / org 之一"
}
```

出现原因：

- 前端传入了不支持的 `tier` 值

### 9.2 `404 Not Found`：`session_id` 不存在

```json
{
  "detail": "Session 不存在"
}
```

出现原因：

- session 已过期
- session 未创建成功
- 前端传错了 `session_id`

### 9.3 `400 Bad Request`：未完成该层级解析

```json
{
  "detail": "该 session 尚未解析 field=C1 tier=org 的数据，请先调用 /api/geo/parse-tier 解析 org 层"
}
```

出现原因：

- 还没有执行对应的解析任务
- 或解析结果尚未写入当前 session

前端建议处理方式：

- 提示用户先完成对应字段和层级的解析
- 或自动跳转/引导到解析步骤

---

## 10. 当前接口的前端接入建议

对于本次固定请求：

```text
GET /api/geo/entity-matrix?session_id=a302e588567e4d4c9f9fa378a565062d&field=C1&tier=org&top_n=20&threshold=0
```

推荐前端最少做以下 4 块展示：

1. 顶部统计卡片
   - `total_papers`
   - `papers_with_entity`
   - `papers_without_entity`
   - `total_pairs`

2. 共现矩阵热力图
   - `entities + matrix`

3. 机构合作网络图
   - `nodes + validEdges`

4. 机构列表或详情抽屉
   - 节点名称
   - 频次
   - 坐标

---

## 11. 一句话给前端的理解

这个接口返回的是：

```text
“文献级机构共现矩阵 + 节点列表 + 边列表”
```

其中：

- `entities + matrix` 适合画矩阵热力图
- `nodes + edges` 适合画关系网络图
- `nodes` 里有坐标时，还可以联动地图展示
