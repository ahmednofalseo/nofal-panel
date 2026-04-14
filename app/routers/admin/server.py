"""
Admin Server Router - Server Management (WHM Server Config)
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin_user
from app.services.system import SystemService
from app.services.nginx import NginxService
from app.services.mysql_service import MySQLService
from app.services.postfix import MailService
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin-server"])


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    from app.models.user import User
    from app.models.domain import Domain
    from app.models.package import Package

    stats = SystemService.get_dashboard_stats()
    total_accounts = db.query(User).filter(User.role != "admin").count()
    total_domains = db.query(Domain).count()
    total_packages = db.query(Package).count()
    suspended = db.query(User).filter(User.is_suspended == True).count()
    recent_accounts = db.query(User).filter(User.role != "admin").order_by(User.created_at.desc()).limit(5).all()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": admin,
        "stats": stats, "page": "dashboard",
        "total_accounts": total_accounts,
        "total_domains": total_domains,
        "total_packages": total_packages,
        "suspended_accounts": suspended,
        "recent_accounts": recent_accounts,
    })


@router.get("/server/monitor", response_class=HTMLResponse)
async def server_monitor(request: Request, admin=Depends(get_admin_user)):
    stats = SystemService.get_dashboard_stats()
    return templates.TemplateResponse("admin/monitor.html", {
        "request": request, "user": admin, "stats": stats, "page": "monitor"
    })


@router.get("/server/monitor/api")
async def server_monitor_api(admin=Depends(get_admin_user)):
    """Live stats API for dashboard charts"""
    return JSONResponse({
        "cpu": SystemService.get_cpu_usage(interval=1),
        "memory": SystemService.get_memory_usage(),
        "disk": SystemService.get_disk_usage(),
        "network": SystemService.get_network_usage(),
    })


@router.get("/server/services", response_class=HTMLResponse)
async def server_services(request: Request, admin=Depends(get_admin_user)):
    services = SystemService.get_services_status()
    return templates.TemplateResponse("admin/services.html", {
        "request": request, "user": admin, "services": services, "page": "services"
    })


@router.post("/server/services/{service}/{action}")
async def manage_service(service: str, action: str, admin=Depends(get_admin_user)):
    result = SystemService.manage_service(service, action)
    return JSONResponse(result)


@router.get("/server/logs", response_class=HTMLResponse)
async def server_logs(request: Request, service: str = "nginx", admin=Depends(get_admin_user)):
    logs = SystemService.get_system_logs(service=service, lines=200)
    services_list = ["nginx", "nginx_error", "mysql", "postfix", "auth", "syslog"]
    return templates.TemplateResponse("admin/logs.html", {
        "request": request, "user": admin,
        "logs": logs, "current_service": service,
        "services_list": services_list, "page": "logs"
    })


@router.get("/server/firewall", response_class=HTMLResponse)
async def firewall_page(request: Request, admin=Depends(get_admin_user)):
    rules = SystemService.get_firewall_rules()
    return templates.TemplateResponse("admin/firewall.html", {
        "request": request, "user": admin, "rules": rules, "page": "firewall"
    })


@router.post("/server/firewall/add")
async def add_firewall_rule(
    port: int = Form(...),
    protocol: str = Form("tcp"),
    action: str = Form("allow"),
    admin=Depends(get_admin_user)
):
    result = SystemService.add_firewall_rule(port, protocol, action)
    return JSONResponse(result)


@router.get("/server/processes", response_class=HTMLResponse)
async def processes_page(request: Request, admin=Depends(get_admin_user)):
    processes = SystemService.get_top_processes(limit=30)
    return templates.TemplateResponse("admin/processes.html", {
        "request": request, "user": admin, "processes": processes, "page": "processes"
    })


@router.get("/server/info", response_class=HTMLResponse)
async def server_info(request: Request, admin=Depends(get_admin_user)):
    info = SystemService.get_server_info()
    nginx_status = NginxService.get_status()
    mysql_status = MySQLService.get_server_status()
    mail_status = MailService.get_service_status()
    return templates.TemplateResponse("admin/server_info.html", {
        "request": request, "user": admin,
        "info": info, "nginx": nginx_status,
        "mysql": mysql_status, "mail": mail_status,
        "page": "server_info"
    })


@router.get("/logs/activity", response_class=HTMLResponse)
async def activity_logs(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    from app.models.activity_log import ActivityLog
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(200).all()
    return templates.TemplateResponse("admin/activity_logs.html", {
        "request": request, "user": admin, "logs": logs, "page": "activity_logs"
    })
