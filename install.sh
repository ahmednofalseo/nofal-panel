#!/bin/bash
# =============================================
#   NOFAL PANEL - Auto Installer
#   Supports: Ubuntu 20.04 / 22.04 / Debian 11/12
#   Run as root: sudo bash install.sh
# =============================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

PANEL_DIR="/opt/nofal-panel"
PANEL_PORT=2083
PANEL_USER="nofalpanel"

header() {
  clear
  echo -e "${BLUE}"
  echo "  ███╗   ██╗ ██████╗ ███████╗ █████╗ ██╗     "
  echo "  ████╗  ██║██╔═══██╗██╔════╝██╔══██╗██║     "
  echo "  ██╔██╗ ██║██║   ██║█████╗  ███████║██║     "
  echo "  ██║╚██╗██║██║   ██║██╔══╝  ██╔══██║██║     "
  echo "  ██║ ╚████║╚██████╔╝██║     ██║  ██║███████╗"
  echo "  ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝  ╚═╝╚══════╝"
  echo "                 PANEL  v1.0"
  echo -e "${NC}"
  echo -e "${CYAN}  Hosting Control Panel - Like WHM/cPanel${NC}"
  echo -e "  ─────────────────────────────────────────"
  echo ""
}

log()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
error()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info()   { echo -e "${BLUE}[i]${NC} $1"; }
step()   { echo -e "\n${CYAN}══ $1 ══${NC}"; }

# Check root
check_root() {
  if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root: sudo bash install.sh"
  fi
}

# Detect OS
detect_os() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID; VERSION_ID=$VERSION_ID
  else
    error "Cannot detect OS"
  fi
  if [[ "$OS" != "ubuntu" && "$OS" != "debian" ]]; then
    error "Unsupported OS: $OS. Supported: Ubuntu 20.04/22.04, Debian 11/12"
  fi
  log "OS detected: $OS $VERSION_ID"
}

# Update system
update_system() {
  step "Updating system"
  apt-get update -qq && apt-get upgrade -y -qq
  log "System updated"
}

# Install dependencies
install_dependencies() {
  step "Installing dependencies"
  apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    nginx \
    mysql-server \
    postfix dovecot-core dovecot-imapd dovecot-pop3d \
    bind9 bind9utils \
    vsftpd \
    certbot python3-certbot-nginx \
    fail2ban \
    ufw \
    curl wget git unzip \
    php8.1 php8.1-fpm php8.1-mysql php8.1-curl php8.1-gd \
    php8.1-mbstring php8.1-xml php8.1-zip php8.1-bcmath \
    openssl \
    2>/dev/null || true
  log "All dependencies installed"
}

# Create panel user
create_panel_user() {
  step "Creating panel user"
  if ! id "$PANEL_USER" &>/dev/null; then
    useradd -r -s /bin/false "$PANEL_USER"
    log "Created system user: $PANEL_USER"
  else
    warn "User $PANEL_USER already exists"
  fi
}

# Install panel
install_panel() {
  step "Installing Nofal Panel"

  # Create install directory
  mkdir -p "$PANEL_DIR"

  # Copy files
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [[ "$SCRIPT_DIR" != "$PANEL_DIR" ]]; then
    cp -r "$SCRIPT_DIR"/* "$PANEL_DIR/" 2>/dev/null || true
    log "Files copied to $PANEL_DIR"
  fi

  cd "$PANEL_DIR"

  # Create virtual environment
  python3 -m venv venv
  source venv/bin/activate

  # Install Python requirements
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  log "Python dependencies installed"

  # Copy env file
  if [[ ! -f "$PANEL_DIR/.env" ]]; then
    cp "$PANEL_DIR/.env.example" "$PANEL_DIR/.env"
    log "Created .env file"
  fi

  # Set permissions
  chown -R "$PANEL_USER":"$PANEL_USER" "$PANEL_DIR"
  chmod -R 755 "$PANEL_DIR"
  log "Permissions set"
}

# Configure Nginx for panel
configure_nginx() {
  step "Configuring Nginx"

  cat > /etc/nginx/sites-available/nofal-panel << 'NGINX_CONF'
server {
    listen 2083;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:2084;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300;
    }

    location /static {
        alias /opt/nofal-panel/static;
        expires 7d;
    }
}
NGINX_CONF

  ln -sf /etc/nginx/sites-available/nofal-panel /etc/nginx/sites-enabled/nofal-panel
  nginx -t && systemctl reload nginx
  log "Nginx configured"
}

# Create MySQL databases for panel
configure_mysql() {
  step "Configuring MySQL"
  systemctl start mysql 2>/dev/null || systemctl start mysqld 2>/dev/null || true
  log "MySQL started"
}

# Configure BIND9 DNS
configure_bind9() {
  step "Configuring BIND9 DNS"
  mkdir -p /etc/bind/zones
  chown bind:bind /etc/bind/zones
  chmod 755 /etc/bind/zones

  # Check if local conf has include for zones
  if ! grep -q "zones" /etc/bind/named.conf.local 2>/dev/null; then
    echo 'include "/etc/bind/named.conf.local.zones";' >> /etc/bind/named.conf.local
    touch /etc/bind/named.conf.local.zones
  fi

  systemctl enable bind9 && systemctl start bind9 || true
  log "BIND9 DNS configured"
}

# Configure mail server
configure_mail() {
  step "Configuring Mail Server (Postfix + Dovecot)"

  # Basic Postfix config
  postconf -e "virtual_mailbox_domains = /etc/postfix/virtual_domains"
  postconf -e "virtual_mailbox_base = /var/mail/vhosts"
  postconf -e "virtual_mailbox_maps = hash:/etc/postfix/virtual_mailbox"
  postconf -e "virtual_alias_maps = hash:/etc/postfix/virtual_alias"
  postconf -e "virtual_uid_maps = static:5000"
  postconf -e "virtual_gid_maps = static:5000"

  # Create vmail user
  if ! id vmail &>/dev/null; then
    groupadd -g 5000 vmail
    useradd -g vmail -u 5000 vmail -d /var/mail/vhosts -m
    log "Created vmail user"
  fi

  # Create empty map files
  for f in /etc/postfix/virtual_domains /etc/postfix/virtual_mailbox /etc/postfix/virtual_alias; do
    touch "$f" && postmap "$f" 2>/dev/null || true
  done

  # Dovecot basic
  mkdir -p /etc/dovecot
  touch /etc/dovecot/users
  chmod 600 /etc/dovecot/users

  systemctl enable postfix dovecot && systemctl restart postfix || true
  log "Mail server configured"
}

# Configure FTP (vsftpd)
configure_ftp() {
  step "Configuring FTP Server (vsftpd)"
  mkdir -p /etc/vsftpd/users

  cat > /etc/vsftpd.conf << 'FTP_CONF'
listen=YES
listen_ipv6=NO
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
virtual_use_local_privs=YES
guest_enable=YES
guest_username=vmail
user_config_dir=/etc/vsftpd/users
FTP_CONF

  systemctl enable vsftpd && systemctl restart vsftpd || true
  log "FTP server configured"
}

# Configure firewall
configure_firewall() {
  step "Configuring Firewall (UFW)"
  ufw --force enable
  ufw allow 22/tcp    # SSH
  ufw allow 80/tcp    # HTTP
  ufw allow 443/tcp   # HTTPS
  ufw allow 21/tcp    # FTP
  ufw allow 25/tcp    # SMTP
  ufw allow 110/tcp   # POP3
  ufw allow 143/tcp   # IMAP
  ufw allow 993/tcp   # IMAPS
  ufw allow 995/tcp   # POP3S
  ufw allow 53/tcp    # DNS
  ufw allow 53/udp    # DNS
  ufw allow "$PANEL_PORT"/tcp  # Panel
  log "Firewall configured"
}

# Create systemd service
create_service() {
  step "Creating systemd service"

  cat > /etc/systemd/system/nofal-panel.service << SERVICE
[Unit]
Description=Nofal Panel - Hosting Control Panel
After=network.target mysql.service

[Service]
Type=simple
User=$PANEL_USER
WorkingDirectory=$PANEL_DIR
Environment=PATH=$PANEL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
ExecStart=$PANEL_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 2084 --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  systemctl enable nofal-panel
  systemctl start nofal-panel
  sleep 3

  if systemctl is-active --quiet nofal-panel; then
    log "Nofal Panel service started successfully"
  else
    warn "Service may have failed to start. Check: journalctl -u nofal-panel -n 50"
  fi
}

# Get server IP
get_server_ip() {
  hostname -I | awk '{print $1}' 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP"
}

# Final output
show_completion() {
  SERVER_IP=$(get_server_ip)
  echo ""
  echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║          NOFAL PANEL INSTALLED SUCCESSFULLY!          ║${NC}"
  echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}Panel URL:${NC}    http://${SERVER_IP}:${PANEL_PORT}"
  echo -e "  ${CYAN}Admin User:${NC}   admin"
  echo -e "  ${CYAN}Admin Pass:${NC}   NofaLPanel@2024"
  echo ""
  echo -e "  ${YELLOW}[WARNING]  IMPORTANT: Change admin password immediately after login!${NC}"
  echo ""
  echo -e "  ${BLUE}Useful Commands:${NC}"
  echo -e "    Start:   systemctl start nofal-panel"
  echo -e "    Stop:    systemctl stop nofal-panel"
  echo -e "    Restart: systemctl restart nofal-panel"
  echo -e "    Logs:    journalctl -u nofal-panel -f"
  echo ""
  echo -e "  ${BLUE}Panel Location:${NC} $PANEL_DIR"
  echo ""
}

# ─── MAIN EXECUTION ──────────────────────────────────────────────────────────
main() {
  header
  check_root
  detect_os
  update_system
  install_dependencies
  create_panel_user
  install_panel
  configure_nginx
  configure_mysql
  configure_bind9
  configure_mail
  configure_ftp
  configure_firewall
  create_service
  show_completion
}

main "$@"
