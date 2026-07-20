# AiGeovis Docker 部署指南

## 目录结构

项目保持以下目录结构即可：

```
AiGeovis/
├── backend/
│   ├── main.py              # 薄入口：create_app()
│   ├── data_service.py      # WoS 解析
│   ├── app/                 # FastAPI factory
│   ├── api/                 # 路由（health / data / parse / …）
│   ├── core/                # sessions / schemas / i18n
│   ├── geo/                 # 解析、地理编码、参考库
│   ├── data/                # 上传与数据质量
│   ├── services/            # 矩阵 / 可视化 / GML
│   ├── requirements.txt
│   └── start.bat
├── demoData/                # Demo 数据
├── Dockerfile
└── docker-compose.yml
```

> WoS 解析已内联为 `backend/data_service.py`，不再依赖历史 `geocode1.1` 目录。

---

## 构建并启动

在项目根目录执行：

```bash
# 构建镜像（首次运行或代码更新后执行）
docker compose build

# 启动服务（后台运行）
docker compose up -d

# 查看运行日志
docker compose logs -f backend

# 停止服务
docker compose down
```

## 验证服务

```bash
curl http://localhost:35696/api/health
```

正常返回：

```json
{"status":"ok","version":"1.2.0"}
```

## 访问 API 文档

部署完成后在浏览器打开：

```
http://<服务器IP>:35696/docs
```

---

## 配置说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 容器端口 | `35696` | 后端 API 监听端口 |
| 宿主机映射 | `35696:35696` | 外部访问端口 |
| 健康检查 | `GET /api/health` | 每 30 秒检查一次 |
| 重启策略 | `unless-stopped` | 除非手动停止，否则始终重启 |

---

## 使用 Systemd 管理（推荐）

创建服务文件 `/etc/systemd/system/aigeovis.service`：

```ini
[Unit]
Description=AiGeovis Backend
Requires=docker.compose.service
After=network.target docker.compose.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/AiGeovis
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

启用并启动：

```bash
sudo systemctl enable aigeovis
sudo systemctl start aigeovis
```

---

## 常用命令

```bash
# 进入容器（调试）
docker exec -it aigeovis-backend /bin/bash

# 查看容器状态
docker ps

# 重启服务
docker compose restart backend

# 重新构建（代码更新后）
docker compose build --no-cache && docker compose up -d
```
