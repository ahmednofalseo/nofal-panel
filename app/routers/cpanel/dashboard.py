"""
cPanel Dashboard Router
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.services.system import SystemService
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel"])


@router.get("/dashboard", response_class=HTMLResponse)
async def cpanel_dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    from app.models.domain import Domain
    from app.models.email_account import EmailAccount
    from app.models.db_account import DatabaseAccount
    from app.models.ftp_account import FtpAccount

    domains_count = db.query(Domain).filter(Domain.user_id == user.id).count()
    email_count = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).count()
    db_count = db.query(DatabaseAccount).filter(DatabaseAccount.user_id == user.id).count()
    ftp_count = db.query(FtpAccount).filter(FtpAccount.user_id == user.id).count()

    disk_percent = 0
    if user.disk_quota_mb > 0:
        disk_percent = min(100, round((user.disk_used_mb / user.disk_quota_mb) * 100))

    bw_percent = 0
    if user.bandwidth_limit_mb > 0:
        bw_percent = min(100, round((user.bandwidth_used_mb / user.bandwidth_limit_mb) * 100))

    cpu_snap = SystemService.get_cpu_usage()
    mem_snap = SystemService.get_memory_usage()

    return templates.TemplateResponse("cpanel/dashboard.html", {
        "request": request, "user": user,
        "domains_count": domains_count,
        "email_count": email_count,
        "db_count": db_count,
        "ftp_count": ftp_count,
        "disk_percent": disk_percent,
        "bw_percent": bw_percent,
        "cpu_host_pct": round(cpu_snap.get("percent") or 0, 1),
        "ram_host_pct": round(mem_snap.get("percent") or 0, 1),
        "page": "dashboard"
    })


FEATURE_LABELS_AR = {
    "disk_usage": "استخدام القرص",
    "backup": "النسخ الاحتياطي",
    "git": "Git™",
    "phpmyadmin": "phpMyAdmin",
    "remote_mysql": "Remote MySQL",
    "addon_domains": "نطاقات إضافية",
    "redirects": "إعادة التوجيه",
    "zone_editor": "محرر المنطقة",
    "forwarders": "الموجهات",
    "autoresponder": "الرد الآلي",
    "spam": "عامل السبام",
    "visitors": "الزوار",
    "errors": "الأخطاء",
    "bandwidth": "تقرير النطاق الترددي",
    "raw_log": "سجل خام",
    "ssh": "SSH",
    "ip_blocker": "حظر IP",
    "hotlink": "Hotlink Protection",
    "multiphp": "MultiPHP",
    "optimize": "تحسين الموقع",
    "ini_editor": "محرر INI",
    "track_dns": "تتبع DNS",
}


@router.get("/feature-unavailable", response_class=HTMLResponse)
async def feature_unavailable(
    request: Request,
    key: str = "",
    label: str = "",
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    display = FEATURE_LABELS_AR.get(key) or (label.replace("+", " ") if label else "هذه الأداة")
    return templates.TemplateResponse(
        "cpanel/feature_unavailable.html",
        {"request": request, "user": user, "label": display, "page": "dashboard"},
    )
