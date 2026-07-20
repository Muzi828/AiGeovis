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
