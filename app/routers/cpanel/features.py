"""
cPanel-style tools: disk, backup, Git, DB remote access, domains extras,
email tools, metrics, security, PHP — stored in UserPreference where needed.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dns.resolver
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_cpanel_user
from app.config import settings
from app.database import get_db
from app.models.domain import DNSRecord, Domain
from app.models.email_account import EmailAccount
from app.models.user_preference import pref_get_json, pref_get_text, pref_set_json, pref_set_text

router = APIRouter(prefix="/cpanel", tags=["cpanel-features"])
templates = Jinja2Templates(directory="app/templates")


def _account_home(user) -> Path:
    return Path(settings.ACCOUNTS_HOME) / user.username


def _safe_tail(path: str, max_lines: int = 80, max_bytes: int = 180_000) -> str:
    try:
        p = Path(path)
        if not p.is_file():
            return f"الملف غير موجود: {path}"
        with p.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return ""
            chunk = min(max_bytes, size)
            f.seek(size - chunk)
            data = f.read().decode("utf-8", errors="replace")
        lines = data.splitlines()
        return "\n".join(lines[-max_lines:])
    except OSError as exc:
        return f"تعذّر القراءة: {exc}"


def _du_summary(home: Path) -> List[Tuple[str, str]]:
    rows: List[Tuple[str, str]] = []
    if not home.is_dir():
        return rows
    for name in ("public_html", "mail", "logs", "tmp"):
        sub = home / name
        if not sub.exists():
            continue
        try:
            out = subprocess.run(
                ["du", "-sh", str(sub)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if out.returncode == 0 and out.stdout.strip():
                parts = out.stdout.strip().split("\t", 1)
                rows.append((parts[1] if len(parts) > 1 else name, parts[0]))
        except (OSError, subprocess.TimeoutExpired):
            rows.append((str(sub), "—"))
    return rows


def _git_roots(home: Path, limit: int = 40) -> List[str]:
    repos: List[str] = []
    if not home.is_dir():
        return repos
    try:
        for p in home.rglob(".git"):
            if p.is_file() or p.is_dir():
                repos.append(str(p.parent.resolve()))
            if len(repos) >= limit:
                break
    except OSError:
        pass
    return sorted(set(repos))


def _resolve_dns(name: str, rtype: str) -> List[str]:
    rtype = (rtype or "A").upper()
    out: List[str] = []
    try:
        ans = dns.resolver.resolve(name, rtype, lifetime=5)
        for r in ans:
            out.append(str(r))
    except Exception as exc:
        out.append(f"خطأ: {exc}")
    return out


# --- Disk -----------------------------------------------------------------

@router.get("/disk-usage", response_class=HTMLResponse)
async def disk_usage(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    home = _account_home(user)
    du_rows = _du_summary(home)
    host_total = host_free = host_used = None
    try:
        usage = shutil.disk_usage(str(home) if home.is_dir() else settings.ACCOUNTS_HOME)
        host_total, host_free, host_used = usage.total, usage.free, usage.used
    except OSError:
        pass
    return templates.TemplateResponse(
        "cpanel/features/disk_usage.html",
        {
            "request": request,
            "user": user,
            "page": "disk_usage",
            "home": str(home),
            "du_rows": du_rows,
            "host_total": host_total,
            "host_free": host_free,
            "host_used": host_used,
        },
    )


# --- Backup ---------------------------------------------------------------

@router.get("/backup", response_class=HTMLResponse)
async def backup_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cfg = pref_get_json(
        db,
        user.id,
        "backup",
        {"enabled": False, "schedule": "weekly", "note": ""},
    )
    return templates.TemplateResponse(
        "cpanel/features/backup.html",
        {"request": request, "user": user, "page": "backup", "cfg": cfg},
    )


@router.post("/backup/save")
async def backup_save(
    enabled: str = Form("0"),
    schedule: str = Form("weekly"),
    note: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    cfg = {
        "enabled": enabled == "1",
        "schedule": schedule if schedule in ("daily", "weekly", "monthly") else "weekly",
        "note": note[:2000],
    }
    pref_set_json(db, user.id, "backup", cfg)
    db.commit()
    return RedirectResponse(url="/cpanel/backup?saved=1", status_code=302)


# --- Git ------------------------------------------------------------------

@router.get("/git", response_class=HTMLResponse)
async def git_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    repos = _git_roots(_account_home(user))
    return templates.TemplateResponse(
        "cpanel/features/git.html",
        {"request": request, "user": user, "page": "git", "repos": repos},
    )


# --- phpMyAdmin -----------------------------------------------------------

@router.get("/phpmyadmin", response_class=HTMLResponse)
async def phpmyadmin_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    url = (settings.PHPMYADMIN_URL or "").strip()
    return templates.TemplateResponse(
        "cpanel/features/phpmyadmin.html",
        {"request": request, "user": user, "page": "phpmyadmin", "pma_url": url},
    )


# --- Remote MySQL ---------------------------------------------------------

@router.get("/remote-mysql", response_class=HTMLResponse)
async def remote_mysql_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    hosts: List[str] = pref_get_json(db, user.id, "remote_mysql_hosts", [])
    if not isinstance(hosts, list):
        hosts = []
    return templates.TemplateResponse(
        "cpanel/features/remote_mysql.html",
        {"request": request, "user": user, "page": "remote_mysql", "hosts": hosts},
    )


@router.post("/remote-mysql/add")
async def remote_mysql_add(
    host: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    host = host.strip()[:255]
    if not host:
        return RedirectResponse(url="/cpanel/remote-mysql", status_code=302)
    hosts: List[str] = pref_get_json(db, user.id, "remote_mysql_hosts", [])
    if not isinstance(hosts, list):
        hosts = []
    if host not in hosts:
        hosts.append(host)
    pref_set_json(db, user.id, "remote_mysql_hosts", hosts)
    db.commit()
    return RedirectResponse(url="/cpanel/remote-mysql", status_code=302)


@router.post("/remote-mysql/remove")
async def remote_mysql_remove(
    host: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    hosts: List[str] = pref_get_json(db, user.id, "remote_mysql_hosts", [])
    if isinstance(hosts, list) and host in hosts:
        hosts.remove(host)
        pref_set_json(db, user.id, "remote_mysql_hosts", hosts)
        db.commit()
    return RedirectResponse(url="/cpanel/remote-mysql", status_code=302)


# --- Addon domains (view) -------------------------------------------------

@router.get("/addon-domains", response_class=HTMLResponse)
async def addon_domains_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    addons = (
        db.query(Domain)
        .filter(Domain.user_id == user.id, Domain.domain_type == "addon")
        .order_by(Domain.domain_name)
        .all()
    )
    return templates.TemplateResponse(
        "cpanel/features/addon_domains.html",
        {"request": request, "user": user, "page": "addon_domains", "addons": addons},
    )


# --- Redirects (domain_type redirect) ------------------------------------

@router.get("/redirects", response_class=HTMLResponse)
async def redirects_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    rules = (
        db.query(Domain)
        .filter(Domain.user_id == user.id, Domain.domain_type == "redirect")
        .order_by(Domain.domain_name)
        .all()
    )
    bases = (
        db.query(Domain)
        .filter(Domain.user_id == user.id, Domain.domain_type.in_(["main", "addon"]))
        .all()
    )
    return templates.TemplateResponse(
        "cpanel/features/redirects.html",
        {"request": request, "user": user, "page": "redirects", "rules": rules, "bases": bases},
    )


# --- Zone editor ----------------------------------------------------------

@router.get("/zone-editor", response_class=HTMLResponse)
async def zone_editor(
    request: Request,
    domain_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    domains = db.query(Domain).filter(Domain.user_id == user.id).order_by(Domain.domain_name).all()
    if not domains:
        return templates.TemplateResponse(
            "cpanel/features/zone_editor.html",
            {
                "request": request,
                "user": user,
                "page": "zone_editor",
                "domains": [],
                "selected": None,
                "records": [],
            },
        )
    selected = None
    if domain_id:
        selected = next((d for d in domains if d.id == domain_id), None)
    if not selected:
        selected = domains[0]
    records = (
        db.query(DNSRecord)
        .filter(DNSRecord.domain_id == selected.id)
        .order_by(DNSRecord.record_type, DNSRecord.name)
        .all()
    )
    return templates.TemplateResponse(
        "cpanel/features/zone_editor.html",
        {
            "request": request,
            "user": user,
            "page": "zone_editor",
            "domains": domains,
            "selected": selected,
            "records": records,
        },
    )


@router.post("/zone-editor/add")
async def zone_editor_add(
    domain_id: int = Form(...),
    record_type: str = Form(...),
    name: str = Form(...),
    value: str = Form(...),
    ttl: int = Form(3600),
    priority: int = Form(0),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    domain = db.query(Domain).filter(Domain.id == domain_id, Domain.user_id == user.id).first()
    if not domain:
        raise HTTPException(status_code=404)
    rec = DNSRecord(
        domain_id=domain.id,
        record_type=record_type.upper()[:10],
        name=name.strip()[:255],
        value=value.strip(),
        ttl=max(60, min(ttl, 86400)),
        priority=max(0, priority),
    )
    db.add(rec)
    db.commit()
    return RedirectResponse(url=f"/cpanel/zone-editor?domain_id={domain.id}", status_code=302)


@router.post("/zone-editor/delete/{record_id}")
async def zone_editor_delete(
    record_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    rec = (
        db.query(DNSRecord)
        .join(Domain)
        .filter(DNSRecord.id == record_id, Domain.user_id == user.id)
        .first()
    )
    dom_id = None
    if rec:
        dom_id = rec.domain_id
        db.delete(rec)
        db.commit()
    if dom_id:
        return RedirectResponse(url=f"/cpanel/zone-editor?domain_id={dom_id}", status_code=302)
    return RedirectResponse(url="/cpanel/zone-editor", status_code=302)


# --- Forwarders / Autoresponder / Spam ------------------------------------

@router.get("/forwarders", response_class=HTMLResponse)
async def forwarders_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    emails = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == user.id)
        .order_by(EmailAccount.email)
        .all()
    )
    return templates.TemplateResponse(
        "cpanel/features/forwarders.html",
        {"request": request, "user": user, "page": "forwarders", "emails": emails},
    )


@router.get("/autoresponder", response_class=HTMLResponse)
async def autoresponder_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    emails = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == user.id)
        .order_by(EmailAccount.email)
        .all()
    )
    return templates.TemplateResponse(
        "cpanel/features/autoresponder.html",
        {"request": request, "user": user, "page": "autoresponder", "emails": emails},
    )


@router.get("/spam", response_class=HTMLResponse)
async def spam_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cfg = pref_get_json(db, user.id, "spam_filter", {"level": "medium", "block_attachments": False})
    return templates.TemplateResponse(
        "cpanel/features/spam.html",
        {"request": request, "user": user, "page": "spam", "cfg": cfg},
    )


@router.post("/spam/save")
async def spam_save(
    level: str = Form("medium"),
    block_attachments: str = Form("0"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    cfg = {
        "level": level if level in ("off", "low", "medium", "high") else "medium",
        "block_attachments": block_attachments == "1",
    }
    pref_set_json(db, user.id, "spam_filter", cfg)
    db.commit()
    return RedirectResponse(url="/cpanel/spam?saved=1", status_code=302)


# --- Metrics --------------------------------------------------------------

@router.get("/metrics/visitors", response_class=HTMLResponse)
async def metrics_visitors(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    log_path = settings.NGINX_ACCESS_LOG
    tail = _safe_tail(log_path, max_lines=100)
    return templates.TemplateResponse(
        "cpanel/features/metrics_visitors.html",
        {
            "request": request,
            "user": user,
            "page": "metrics_visitors",
            "log_path": log_path,
            "tail": tail,
        },
    )


@router.get("/metrics/errors", response_class=HTMLResponse)
async def metrics_errors(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    log_path = settings.NGINX_ERROR_LOG
    tail = _safe_tail(log_path, max_lines=100)
    return templates.TemplateResponse(
        "cpanel/features/metrics_errors.html",
        {
            "request": request,
            "user": user,
            "page": "metrics_errors",
            "log_path": log_path,
            "tail": tail,
        },
    )


@router.get("/metrics/bandwidth", response_class=HTMLResponse)
async def metrics_bandwidth(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    disk_pct = bw_pct = 0
    if user.disk_quota_mb and user.disk_quota_mb > 0:
        disk_pct = min(100, round((user.disk_used_mb / user.disk_quota_mb) * 100))
    if user.bandwidth_limit_mb and user.bandwidth_limit_mb > 0:
        bw_pct = min(100, round((user.bandwidth_used_mb / user.bandwidth_limit_mb) * 100))
    return templates.TemplateResponse(
        "cpanel/features/metrics_bandwidth.html",
        {
            "request": request,
            "user": user,
            "page": "metrics_bandwidth",
            "disk_pct": disk_pct,
            "bw_pct": bw_pct,
        },
    )


@router.get("/metrics/raw-log", response_class=HTMLResponse)
async def metrics_raw_log(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    log_path = settings.NGINX_ACCESS_LOG
    tail = _safe_tail(log_path, max_lines=200)
    return templates.TemplateResponse(
        "cpanel/features/raw_log.html",
        {
            "request": request,
            "user": user,
            "page": "raw_log",
            "log_path": log_path,
            "tail": tail,
        },
    )


# --- Security -------------------------------------------------------------

@router.get("/ssh", response_class=HTMLResponse)
async def ssh_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cfg = pref_get_json(
        db,
        user.id,
        "ssh_prefs",
        {"pubkey": "", "notes": ""},
    )
    return templates.TemplateResponse(
        "cpanel/features/ssh.html",
        {"request": request, "user": user, "page": "ssh", "cfg": cfg},
    )


@router.post("/ssh/save")
async def ssh_save(
    pubkey: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    pref_set_json(
        db,
        user.id,
        "ssh_prefs",
        {"pubkey": pubkey[:4000], "notes": notes[:2000]},
    )
    db.commit()
    return RedirectResponse(url="/cpanel/ssh?saved=1", status_code=302)


@router.get("/ip-blocker", response_class=HTMLResponse)
async def ip_blocker_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    ips: List[str] = pref_get_json(db, user.id, "blocked_ips", [])
    if not isinstance(ips, list):
        ips = []
    return templates.TemplateResponse(
        "cpanel/features/ip_blocker.html",
        {"request": request, "user": user, "page": "ip_blocker", "ips": ips},
    )


@router.post("/ip-blocker/add")
async def ip_blocker_add(
    ip: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    ip = ip.strip()[:80]
    ips: List[str] = pref_get_json(db, user.id, "blocked_ips", [])
    if not isinstance(ips, list):
        ips = []
    if ip and ip not in ips:
        ips.append(ip)
    pref_set_json(db, user.id, "blocked_ips", ips)
    db.commit()
    return RedirectResponse(url="/cpanel/ip-blocker", status_code=302)


@router.post("/ip-blocker/remove")
async def ip_blocker_remove(
    ip: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    ips: List[str] = pref_get_json(db, user.id, "blocked_ips", [])
    if isinstance(ips, list) and ip in ips:
        ips.remove(ip)
        pref_set_json(db, user.id, "blocked_ips", ips)
        db.commit()
    return RedirectResponse(url="/cpanel/ip-blocker", status_code=302)


@router.get("/hotlink", response_class=HTMLResponse)
async def hotlink_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cfg = pref_get_json(db, user.id, "hotlink", {"enabled": False, "allow": []})
    if not isinstance(cfg.get("allow"), list):
        cfg["allow"] = []
    return templates.TemplateResponse(
        "cpanel/features/hotlink.html",
        {"request": request, "user": user, "page": "hotlink", "cfg": cfg},
    )


@router.post("/hotlink/save")
async def hotlink_save(
    enabled: str = Form("0"),
    allow_text: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    allow = [x.strip() for x in allow_text.replace(",", "\n").splitlines() if x.strip()][:50]
    pref_set_json(
        db,
        user.id,
        "hotlink",
        {"enabled": enabled == "1", "allow": allow},
    )
    db.commit()
    return RedirectResponse(url="/cpanel/hotlink?saved=1", status_code=302)


# --- Software -------------------------------------------------------------

@router.get("/multiphp", response_class=HTMLResponse)
async def multiphp_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    doms = db.query(Domain).filter(Domain.user_id == user.id).order_by(Domain.domain_name).all()
    versions: Dict[str, str] = pref_get_json(db, user.id, "php_versions", {})
    if not isinstance(versions, dict):
        versions = {}
    return templates.TemplateResponse(
        "cpanel/features/multiphp.html",
        {"request": request, "user": user, "page": "multiphp", "domains": doms, "versions": versions},
    )


@router.post("/multiphp/set")
async def multiphp_set(
    domain_name: str = Form(...),
    php_version: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    domain_name = domain_name.strip()[:255]
    dom = (
        db.query(Domain)
        .filter(Domain.user_id == user.id, Domain.domain_name == domain_name)
        .first()
    )
    if not dom:
        return RedirectResponse(url="/cpanel/multiphp?error=domain", status_code=302)
    ver = php_version.strip()[:16]
    if ver not in ("8.0", "8.1", "8.2", "8.3", "8.4", "7.4"):
        ver = "8.2"
    versions: Dict[str, str] = pref_get_json(db, user.id, "php_versions", {})
    if not isinstance(versions, dict):
        versions = {}
    versions[domain_name] = ver
    pref_set_json(db, user.id, "php_versions", versions)
    db.commit()
    return RedirectResponse(url="/cpanel/multiphp?saved=1", status_code=302)


@router.get("/optimize", response_class=HTMLResponse)
async def optimize_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cfg = pref_get_json(
        db,
        user.id,
        "site_optimize",
        {"gzip": True, "browser_cache": True, "minify_static": False},
    )
    return templates.TemplateResponse(
        "cpanel/features/optimize.html",
        {"request": request, "user": user, "page": "optimize", "cfg": cfg},
    )


@router.post("/optimize/save")
async def optimize_save(
    gzip: str = Form("0"),
    browser_cache: str = Form("0"),
    minify_static: str = Form("0"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    cfg = {
        "gzip": gzip == "1",
        "browser_cache": browser_cache == "1",
        "minify_static": minify_static == "1",
    }
    pref_set_json(db, user.id, "site_optimize", cfg)
    db.commit()
    return RedirectResponse(url="/cpanel/optimize?saved=1", status_code=302)


@router.get("/ini-editor", response_class=HTMLResponse)
async def ini_editor_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    snippet = pref_get_text(db, user.id, "user_php_ini", "; Nofal Panel — مقتطف يُطبَّق يدوياً على الخادم\n")
    return templates.TemplateResponse(
        "cpanel/features/ini_editor.html",
        {"request": request, "user": user, "page": "ini_editor", "snippet": snippet},
    )


@router.post("/ini-editor/save")
async def ini_editor_save(
    snippet: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    pref_set_text(db, user.id, "user_php_ini", snippet[:16000])
    db.commit()
    return RedirectResponse(url="/cpanel/ini-editor?saved=1", status_code=302)


# --- Track DNS ------------------------------------------------------------

@router.get("/track-dns", response_class=HTMLResponse)
async def track_dns_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    return templates.TemplateResponse(
        "cpanel/features/track_dns.html",
        {"request": request, "user": user, "page": "track_dns", "result": None, "q": "", "rtype": "A"},
    )


@router.post("/track-dns", response_class=HTMLResponse)
async def track_dns_post(
    request: Request,
    q: str = Form(...),
    rtype: str = Form("A"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    q = q.strip()[:253]
    rtype = (rtype or "A").upper()[:5]
    result = _resolve_dns(q, rtype) if q else []
    return templates.TemplateResponse(
        "cpanel/features/track_dns.html",
        {
            "request": request,
            "user": user,
            "page": "track_dns",
            "result": result,
            "q": q,
            "rtype": rtype,
        },
    )
