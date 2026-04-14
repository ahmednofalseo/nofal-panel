#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/nofal-panel}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

LOG_DIR="${LOG_DIR:-$APP_DIR/logs/deploy}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deploy-$(date +%Y%m%d-%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

red() { printf "\033[0;31m%s\033[0m\n" "$*"; }
grn() { printf "\033[0;32m%s\033[0m\n" "$*"; }
ylw() { printf "\033[1;33m%s\033[0m\n" "$*"; }
blu() { printf "\033[0;34m%s\033[0m\n" "$*"; }

step() { blu "==> $*"; }
ok() { grn "[OK] $*"; }
warn() { ylw "[WARN] $*"; }
die() { red "[FAIL] $*"; exit 1; }

INDEX_URLS=(
  "${PIP_INDEX_URL:-}"
  "${PIP_EXTRA_INDEX_URL:-}"
  "https://pypi.org/simple"
  "https://pypi.python.org/simple"
)

dedup_indexes() {
  local -a out=()
  local seen="|"
  for x in "${INDEX_URLS[@]}"; do
    x="$(echo "${x:-}" | xargs || true)"
    [[ -z "$x" ]] && continue
    if [[ "$seen" != *"|$x|"* ]]; then
      out+=("$x")
      seen="${seen}${x}|"
    fi
  done
  INDEX_URLS=("${out[@]}")
}

ensure_venv() {
  step "Ensure venv"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
  ok "venv ready: $VENV_DIR"
}

upgrade_pip_toolchain() {
  step "Upgrade pip toolchain"
  "$VENV_DIR/bin/python" -m pip install -q --upgrade pip setuptools wheel
  ok "pip/setuptools/wheel upgraded"
}

preflight() {
  step "Preflight checks"
  VENV_PYTHON="$VENV_DIR/bin/python" "$VENV_DIR/bin/python" "$APP_DIR/scripts/preflight.py" || warn "preflight reported issues (continuing)"
}

pip_install_with_indexes() {
  local req_file="$1"
  local extra_args="${2:-}"

  for idx in "${INDEX_URLS[@]}"; do
    step "pip install ($req_file) using index: $idx"
    set +e
    # shellcheck disable=SC2086
    "$VENV_DIR/bin/python" -m pip install --disable-pip-version-check -r "$req_file" --index-url "$idx" $extra_args
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
      ok "installed: $req_file via $idx"
      return 0
    fi
    warn "install failed via $idx (rc=$rc). Trying next index..."
  done
  return 1
}

install_dependencies() {
  step "Install dependencies (lock preferred)"

  if [[ -f "$APP_DIR/requirements.lock.txt" ]]; then
    if pip_install_with_indexes "$APP_DIR/requirements.lock.txt" ""; then
      ok "dependencies installed from lock"
      return 0
    fi
    warn "lock install failed; falling back to flexible requirements"
  fi

  [[ -f "$APP_DIR/requirements.txt" ]] || die "missing requirements.txt"
  pip_install_with_indexes "$APP_DIR/requirements.txt" "" || die "dependency installation failed on all indexes"
  ok "dependencies installed from flexible requirements"
}

alembic_stamp_or_upgrade() {
  step "DB migrations (stamp/upgrade)"
  if [[ -x "$VENV_DIR/bin/alembic" ]] && [[ -f "$APP_DIR/alembic.ini" ]]; then
    # If the DB already has tables (older create_all deployments), stamping prevents 'already exists' errors.
    "$VENV_DIR/bin/alembic" -c "$APP_DIR/alembic.ini" stamp head || true
    "$VENV_DIR/bin/alembic" -c "$APP_DIR/alembic.ini" upgrade head || true
    ok "alembic attempted"
  else
    warn "alembic not configured; skipping"
  fi
}

restart_services() {
  step "Restart services"
  systemctl restart nofal-panel-admin 2>/dev/null || true
  systemctl restart nofal-panel-user 2>/dev/null || true
  systemctl restart nofal-panel-celery-worker 2>/dev/null || true
  systemctl restart nofal-panel-celery-beat 2>/dev/null || true
  systemctl restart nofal-panel 2>/dev/null || true
  systemctl reload nginx 2>/dev/null || true
  ok "service restart requested"
}

main() {
  dedup_indexes
  step "Deploy start (logs: $LOG_FILE)"
  [[ -d "$APP_DIR" ]] || die "APP_DIR not found: $APP_DIR"

  ensure_venv
  upgrade_pip_toolchain
  preflight
  install_dependencies
  alembic_stamp_or_upgrade
  restart_services
  ok "Deploy finished"
}

main "$@"

