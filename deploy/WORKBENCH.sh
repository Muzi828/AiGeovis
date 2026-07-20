#!/usr/bin/env bash
# Paste into Aliyun ECS「远程连接」terminal as root (or sudo bash).
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y git curl ca-certificates
elif command -v yum >/dev/null 2>&1; then
  yum install -y git curl
fi

mkdir -p /opt
cd /opt
rm -rf AiGeovis
git clone --depth 1 https://gitee.com/lys_828/AiGeovis.git AiGeovis \
  || git clone --depth 1 https://github.com/Muzi828/AiGeovis.git AiGeovis

chmod +x /opt/AiGeovis/deploy/setup-server.sh
bash /opt/AiGeovis/deploy/setup-server.sh

echo
echo "==== verify ===="
curl -fsS http://127.0.0.1:35696/api/health || true
curl -fsS http://127.0.0.1/api/health || true
echo
echo "DNS: set A record @ -> 8.159.143.118 then open https://ai4safe.cn/"
echo "Or open http://8.159.143.118/ now (HTTP)."
