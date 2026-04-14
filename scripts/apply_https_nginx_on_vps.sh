#!/usr/bin/env bash
# Run on the VPS as root after you can SSH in.
# Pulls latest main, sets ADMIN_PUBLIC_PORT=443, installs Nginx config, reloads stack.

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/nofal-panel}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
NGX_SRC="$APP_DIR/ops/nginx/nofal-panel.conf"
# Canonical site name on existing installs (avoid duplicate sites-enabled entries)
NGX_AVAIL="${NGX_AVAIL:-/etc/nginx/sites-available/nofal-panel}"
NGX_EN="${NGX_EN:-/etc/nginx/sites-enabled/nofal-panel}"

die() { echo "[FAIL] $*" >&2; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "Run as root (sudo bash $0)"
[[ -d "$APP_DIR/.git" ]] || die "APP_DIR is not a git repo: $APP_DIR"

cd "$APP_DIR"
git fetch origin main
git pull --ff-only origin main || die "git pull failed"

if [[ -f "$ENV_FILE" ]]; then
  if grep -q '^ADMIN_PUBLIC_PORT=' "$ENV_FILE"; then
    sed -i.bak 's/^ADMIN_PUBLIC_PORT=.*/ADMIN_PUBLIC_PORT=443/' "$ENV_FILE"
  else
    printf '\nADMIN_PUBLIC_PORT=443\n' >> "$ENV_FILE"
  fi
else
  die "Missing $ENV_FILE — copy from .env.example and configure first"
fi

[[ -f "$NGX_SRC" ]] || die "Missing $NGX_SRC"

cp -a "$NGX_SRC" "$NGX_AVAIL"
ln -sf "$NGX_AVAIL" "$NGX_EN"
# Remove duplicate enable left by older script versions
rm -f /etc/nginx/sites-enabled/nofal-panel.conf

nginx -t
systemctl reload nginx

if [[ -x "$APP_DIR/scripts/deploy.sh" ]]; then
  bash "$APP_DIR/scripts/deploy.sh"
else
  systemctl restart nofal-panel-admin 2>/dev/null || true
  systemctl restart nofal-panel-user 2>/dev/null || true
fi

echo "[OK] HTTPS 443 → admin; ADMIN_PUBLIC_PORT=443. Test: curl -k -sI https://127.0.0.1/"
