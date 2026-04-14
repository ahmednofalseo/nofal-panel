#!/bin/bash
# Nofal Panel Uninstaller

echo "[WARNING]  This will remove Nofal Panel from your server."
read -p "Are you sure? Type YES to confirm: " confirm

if [[ "$confirm" != "YES" ]]; then
  echo "Cancelled."
  exit 0
fi

systemctl stop nofal-panel 2>/dev/null
systemctl disable nofal-panel 2>/dev/null
rm -f /etc/systemd/system/nofal-panel.service
systemctl daemon-reload
rm -f /etc/nginx/sites-available/nofal-panel
rm -f /etc/nginx/sites-enabled/nofal-panel
systemctl reload nginx
rm -rf /opt/nofal-panel

echo "[OK] Nofal Panel removed successfully."
