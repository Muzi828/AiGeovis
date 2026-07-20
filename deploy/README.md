# Deploy AiGeovis to ai4safe.cn

Target: ECS `8.159.143.118` · domain `ai4safe.cn` · frontend `/` · API `/api`.

## 1. DNS (Aliyun console)

| Host | Type | Value           |
|------|------|-----------------|
| `@`  | A    | `8.159.143.118` |
| `www`| A    | `8.159.143.118` |

TTL: 600s. Verify (from a machine without fake local DNS):

```bash
nslookup ai4safe.cn 223.5.5.5
# expect: 8.159.143.118
```

## 2. Security group

Inbound allow:

- TCP **80**
- TCP **443**
- TCP **22** (SSH; restrict source if possible)

Do **not** need to expose `35696` publicly.

## 3. Local prep (Windows)

```powershell
cd AiGeovis_frontend
npm ci
npm run build
```

Upload repo + `AiGeovis_frontend/dist` to the server, e.g.:

```powershell
# requires OpenSSH client + key/password
scp -r AiGeovis_backend AiGeovis_frontend\dist deploy root@8.159.143.118:/opt/AiGeovis/
# adjust layout so server has:
#   /opt/AiGeovis/AiGeovis_backend/
#   /opt/AiGeovis/AiGeovis_frontend/dist/
#   /opt/AiGeovis/deploy/
```

Or from WSL/Git Bash with rsync.

## 4. On the server

### Option A — Aliyun Workbench / 远程连接（推荐，无需本机 SSH 密钥）

在 ECS 控制台点「远程连接」→ 打开终端后执行：

```bash
# 安装 git（如无）
command -v git >/dev/null || (apt-get update -y && apt-get install -y git) || yum install -y git

sudo mkdir -p /opt && cd /opt
sudo rm -rf AiGeovis
# 优先 Gitee；若失败改用 GitHub
sudo git clone --depth 1 https://gitee.com/lys_828/AiGeovis.git AiGeovis \
  || sudo git clone --depth 1 https://github.com/Muzi828/AiGeovis.git AiGeovis

# 前端 dist 不在 git 中：用本机上传的包，或在有内存的机器 build 后 scp
# 若已上传 aigeovis-ai4safe.tgz：
#   cd /opt && sudo tar -xzf aigeovis-ai4safe.tgz

cd /opt/AiGeovis
# 若只有源码无 dist，请先在 Windows 运行 deploy/pack-release.ps1 并 scp tarball
sudo bash deploy/setup-server.sh
```

### Option B — 本机一键上传（需 SSH 密码或密钥）

```powershell
cd AiGeovis_code   # 仓库根目录
.\deploy\upload-and-deploy.ps1 -User root -HostIp 8.159.143.118
# 或密钥：
# .\deploy\upload-and-deploy.ps1 -User root -IdentityFile C:\Users\你\.ssh\id_rsa
```

```bash
sudo bash /opt/AiGeovis/deploy/setup-server.sh
```

Manual fallback:

```bash
# backend
cd /opt/AiGeovis/AiGeovis_backend
docker compose up -d --build
curl http://127.0.0.1:35696/api/health

# static + nginx
sudo mkdir -p /var/www/aigeovis
sudo rsync -a --delete /opt/AiGeovis/AiGeovis_frontend/dist/ /var/www/aigeovis/
sudo cp /opt/AiGeovis/deploy/nginx-ai4safe.conf /etc/nginx/conf.d/ai4safe.cn.conf
sudo nginx -t && sudo systemctl reload nginx

# HTTPS
sudo certbot --nginx -d ai4safe.cn -d www.ai4safe.cn
```

## 5. Verify

```bash
curl -fsS http://ai4safe.cn/api/health
curl -I https://ai4safe.cn/
```

Browser: open Demo → map / table.

## Notes

- 2 GiB RAM: build frontend **locally**, not on the ECS.
- Mainland ICP filing may be required for public 80/443; if blocked, complete备案 first.
- Auth/login still points at external citeinsight APIs; use `VITE_DISABLE_AUTH=true` at build time if you need open access:

```powershell
$env:VITE_DISABLE_AUTH='true'
npm run build
```
