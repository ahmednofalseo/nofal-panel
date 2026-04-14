#!/bin/bash
# Run ON THE VPS as root — clones/pulls nofal-panel, venv, systemd, nginx :80 -> :2083
set -euo pipefail

PANEL_DIR="${PANEL_DIR:-/opt/nofal-panel}"
REPO="${REPO:-https://github.com/ahmednofalseo/nofal-panel.git}"
PANEL_PORT="${PANEL_PORT:-2083}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx python3-venv python3-pip git openssl curl

if [[ ! -d "$PANEL_DIR/.git" ]]; then
  git clone "$REPO" "$PANEL_DIR"
else
  cd "$PANEL_DIR" && git pull --ff-only
fi

cd "$PANEL_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

if [[ ! -f .env ]]; then
  cp .env.example .env
fi
SK=$(openssl rand -hex 32)
if grep -q '^SECRET_KEY=' .env; then
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$SK|" .env
else
  echo "SECRET_KEY=$SK" >> .env
fi
sed -i 's/^PANEL_HOST=.*/PANEL_HOST=127.0.0.1/' .env || true

cat > /etc/systemd/system/nofal-panel.service << UNIT
[Unit]
Description=Nofal Panel (FastAPI / uvicorn)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$PANEL_DIR
Environment=PATH=$PANEL_DIR/venv/bin
ExecStart=$PANEL_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $PANEL_PORT --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable nofal-panel
systemctl restart nofal-panel

cat > /etc/nginx/sites-available/nofal-panel << 'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 100M;
    location / {
        proxy_pass http://127.0.0.1:2083;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/nofal-panel /etc/nginx/sites-enabled/nofal-panel
nginx -t
systemctl reload nginx

# Firewall (if ufw exists)
if command -v ufw >/dev/null 2>&1; then
  ufw allow OpenSSH >/dev/null 2>&1 || true
  ufw allow 80/tcp >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
  ufw --force enable >/dev/null 2>&1 || true
fi

sleep 2
systemctl is-active nofal-panel
curl -sI -o /dev/null -w "%{http_code}" http://127.0.0.1/ || true
echo ""
echo "OK: Panel backend on 127.0.0.1:$PANEL_PORT via nginx :80"
