#!/usr/bin/env bash
# Run on ECS as root (or sudo): bash setup-server.sh
set -euo pipefail

DOMAIN="${DOMAIN:-ai4safe.cn}"
APP_ROOT="${APP_ROOT:-/opt/AiGeovis}"
WEB_ROOT="${WEB_ROOT:-/var/www/aigeovis}"
BACKEND_DIR="${APP_ROOT}/AiGeovis_backend"

echo "==> Installing packages (nginx, docker, certbot if missing)"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y nginx curl ca-certificates
  if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sh
  fi
  apt-get install -y certbot python3-certbot-nginx || true
elif command -v yum >/dev/null 2>&1; then
  yum install -y nginx curl
  if ! command -v docker >/dev/null 2>&1; then
    yum install -y yum-utils
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo || true
    yum install -y docker-ce docker-ce-cli containerd.io || yum install -y docker
  fi
  systemctl enable docker --now || true
  yum install -y certbot python3-certbot-nginx || true
else
  echo "Unsupported package manager; install nginx/docker/certbot manually."
  exit 1
fi

systemctl enable nginx --now || true
systemctl enable docker --now || true

echo "==> Web root: ${WEB_ROOT}"
mkdir -p "${WEB_ROOT}" /var/www/certbot
if [[ -d "${APP_ROOT}/deploy/www" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${APP_ROOT}/deploy/www/" "${WEB_ROOT}/"
  else
    rm -rf "${WEB_ROOT:?}/"*
    cp -a "${APP_ROOT}/deploy/www/." "${WEB_ROOT}/"
  fi
elif [[ -d "${APP_ROOT}/AiGeovis_frontend/dist" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${APP_ROOT}/AiGeovis_frontend/dist/" "${WEB_ROOT}/"
  else
    rm -rf "${WEB_ROOT:?}/"*
    cp -a "${APP_ROOT}/AiGeovis_frontend/dist/." "${WEB_ROOT}/"
  fi
elif [[ -d "${APP_ROOT}/dist" ]]; then
  cp -a "${APP_ROOT}/dist/." "${WEB_ROOT}/"
else
  echo "WARN: frontend dist not found under ${APP_ROOT}; upload dist first."
fi

echo "==> Nginx site config"
CONF_SRC="${APP_ROOT}/deploy/nginx-ai4safe.conf"
if [[ -f /etc/nginx/sites-available/default ]] || [[ -d /etc/nginx/sites-available ]]; then
  cp "${CONF_SRC}" "/etc/nginx/sites-available/${DOMAIN}"
  ln -sfn "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
  rm -f /etc/nginx/sites-enabled/default || true
else
  cp "${CONF_SRC}" "/etc/nginx/conf.d/${DOMAIN}.conf"
fi
nginx -t
systemctl reload nginx

echo "==> Backend (docker compose)"
if [[ ! -d "${BACKEND_DIR}" ]]; then
  echo "ERROR: ${BACKEND_DIR} missing"
  exit 1
fi
cd "${BACKEND_DIR}"
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    docker compose up -d --build
  else
    docker-compose up -d --build
  fi
else
  echo "ERROR: docker not installed"
  exit 1
fi

echo "==> Health check (local)"
sleep 3
curl -fsS "http://127.0.0.1:35696/api/health" || true
curl -fsS "http://127.0.0.1/api/health" || true

echo "==> Optional HTTPS (certbot)"
if command -v certbot >/dev/null 2>&1; then
  certbot --nginx -d "${DOMAIN}" -d "www.${DOMAIN}" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect || \
    echo "certbot skipped/failed (DNS/备案未就绪时可稍后重试)"
fi

echo "Done. Open http://${DOMAIN}/ or https://${DOMAIN}/"
