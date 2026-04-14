"""
Admin Packages Router - Hosting Package/Plan Management
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin_user
from app.models.package import Package
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin-packages"])


@router.get("/packages", response_class=HTMLResponse)
async def list_packages(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    packages = db.query(Package).all()
    return templates.TemplateResponse("admin/packages.html", {
        "request": request, "user": admin, "packages": packages, "page": "packages"
    })


@router.get("/packages/create", response_class=HTMLResponse)
async def create_package_page(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return templates.TemplateResponse("admin/packages_create.html", {
        "request": request, "user": admin, "page": "packages"
    })


@router.post("/packages/create")
async def create_package(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    disk_quota_mb: int = Form(1024),
    bandwidth_limit_mb: int = Form(10240),
    email_limit: int = Form(10),
    db_limit: int = Form(5),
    ftp_limit: int = Form(5),
    subdomain_limit: int = Form(10),
    addon_domain_limit: int = Form(2),
    parked_domain_limit: int = Form(5),
    has_ssh: bool = Form(False),
    has_cron: bool = Form(True),
    has_ssl: bool = Form(True),
    has_backup: bool = Form(True),
    php_version: str = Form("8.1"),
    max_upload_size_mb: int = Form(128),
    max_execution_time: int = Form(300),
    memory_limit_mb: int = Form(256),
    price_monthly: float = Form(0.0),
    price_yearly: float = Form(0.0),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    if db.query(Package).filter(Package.name == name).first():
        return templates.TemplateResponse("admin/packages_create.html", {
            "request": request, "user": admin,
            "error": f"Package '{name}' already exists"
        })

    package = Package(
        name=name, description=description,
        disk_quota_mb=disk_quota_mb, bandwidth_limit_mb=bandwidth_limit_mb,
        email_limit=email_limit, db_limit=db_limit,
        ftp_limit=ftp_limit, subdomain_limit=subdomain_limit,
        addon_domain_limit=addon_domain_limit, parked_domain_limit=parked_domain_limit,
        has_ssh=has_ssh, has_cron=has_cron, has_ssl=has_ssl, has_backup=has_backup,
        php_version=php_version, max_upload_size_mb=max_upload_size_mb,
        max_execution_time=max_execution_time, memory_limit_mb=memory_limit_mb,
        price_monthly=price_monthly, price_yearly=price_yearly,
    )
    db.add(package)
    db.commit()
    return RedirectResponse(url="/admin/packages?success=Package+created", status_code=302)


@router.get("/packages/{pkg_id}/edit", response_class=HTMLResponse)
async def edit_package_page(pkg_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    package = db.query(Package).filter(Package.id == pkg_id).first()
    if not package:
        return RedirectResponse(url="/admin/packages")
    return templates.TemplateResponse("admin/packages_edit.html", {
        "request": request, "user": admin, "package": package, "page": "packages"
    })


@router.post("/packages/{pkg_id}/edit")
async def edit_package(
    pkg_id: int, request: Request,
    name: str = Form(...),
    description: str = Form(""),
    disk_quota_mb: int = Form(1024),
    bandwidth_limit_mb: int = Form(10240),
    email_limit: int = Form(10),
    db_limit: int = Form(5),
    ftp_limit: int = Form(5),
    php_version: str = Form("8.1"),
    has_ssh: bool = Form(False),
    has_ssl: bool = Form(True),
    price_monthly: float = Form(0.0),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    package = db.query(Package).filter(Package.id == pkg_id).first()
    if package:
        package.name = name
        package.description = description
        package.disk_quota_mb = disk_quota_mb
        package.bandwidth_limit_mb = bandwidth_limit_mb
        package.email_limit = email_limit
        package.db_limit = db_limit
        package.ftp_limit = ftp_limit
        package.php_version = php_version
        package.has_ssh = has_ssh
        package.has_ssl = has_ssl
        package.price_monthly = price_monthly
        db.commit()
    return RedirectResponse(url="/admin/packages?success=Package+updated", status_code=302)


@router.post("/packages/{pkg_id}/delete")
async def delete_package(pkg_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    package = db.query(Package).filter(Package.id == pkg_id).first()
    if package and len(package.users) == 0:
        db.delete(package)
        db.commit()
    return RedirectResponse(url="/admin/packages?success=Package+deleted", status_code=302)
