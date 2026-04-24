"""
Admin Accounts Router - WHM Account Management
Create, Terminate, Suspend, Modify hosting accounts
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.auth import get_admin_user, get_password_hash
from app.models.user import User
from app.models.package import Package
from app.models.domain import Domain
from app.models.activity_log import ActivityLog
from app.config import settings
from app.services.account_manager import AccountManager
from app.services.ports import PortAllocatorService
from app.services.account_provisioning import AccountProvisioningService
from app.templating import templates

router = APIRouter(prefix="/admin", tags=["admin-accounts"])


@router.get("/accounts", response_class=HTMLResponse)
async def list_accounts(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    accounts = db.query(User).filter(User.role != "admin").all()
    return templates.TemplateResponse("admin/accounts.html", {
        "request": request, "user": admin, "accounts": accounts, "page": "accounts"
    })


@router.get("/accounts/create", response_class=HTMLResponse)
async def create_account_page(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    packages = db.query(Package).filter(Package.is_active == True).all()
    return templates.TemplateResponse(
        "admin/accounts_create.html",
        {
            "request": request,
            "user": admin,
            "packages": packages,
            "page": "accounts",
            "default_server_ip": settings.PANEL_PUBLIC_IP or "",
        },
    )


@router.post("/accounts/create")
async def create_account(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    domain: str = Form(...),
    package_id: int = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    company: str = Form(""),
    ip_address: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    # Visible in journalctl when diagnosing hangs (nginx only logs after response completes).
    print(f"[nofal] CREATE_ACCOUNT POST start username={username!r} domain={domain!r}", flush=True)
    packages = db.query(Package).filter(Package.is_active == True).all()

    # Validate
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("admin/accounts_create.html", {
            "request": request, "user": admin, "packages": packages,
            "error": f"Username '{username}' already exists"
        })

    if db.query(User).filter(User.email == email).first():
        return templates.TemplateResponse("admin/accounts_create.html", {
            "request": request, "user": admin, "packages": packages,
            "error": f"Email '{email}' already exists"
        })

    package = db.query(Package).filter(Package.id == package_id).first()
    if not package:
        return templates.TemplateResponse("admin/accounts_create.html", {
            "request": request, "user": admin, "packages": packages,
            "error": "Invalid package selected"
        })

    # Create DB record
    new_user = User(
        username=username, email=email,
        hashed_password=get_password_hash(password),
        role="user", first_name=first_name, last_name=last_name,
        company=company, primary_domain=domain,
        ip_address=ip_address, package_id=package_id,
        server_user=username,
        disk_quota_mb=package.disk_quota_mb,
        bandwidth_limit_mb=package.bandwidth_limit_mb,
        email_limit=package.email_limit,
        db_limit=package.db_limit,
        ftp_limit=package.ftp_limit,
        subdomain_limit=package.subdomain_limit,
        addon_domain_limit=package.addon_domain_limit,
    )
    db.add(new_user)
    db.flush()

    # Create server resources
    pkg_dict = {
        "php_version": package.php_version,
        "max_upload_size_mb": package.max_upload_size_mb,
        "memory_limit_mb": package.memory_limit_mb,
        "max_execution_time": package.max_execution_time,
        "package_id": package.id,
        "disk_quota_mb": package.disk_quota_mb,
        "bandwidth_limit_mb": package.bandwidth_limit_mb,
        "email_limit": package.email_limit,
        "db_limit": package.db_limit,
        "ftp_limit": package.ftp_limit,
        "subdomain_limit": package.subdomain_limit,
        "addon_domain_limit": package.addon_domain_limit,
    }
    # Use enterprise provisioning wrapper (ports + domain row).
    prov = AccountProvisioningService.create_account(
        db,
        new_user,
        plaintext_password=password,
        domain=domain,
        ip_address=ip_address,
        package=pkg_dict,
    )
    result = prov.details.get("result") if prov.details else {"success": prov.success, "error": prov.error}

    if result["success"]:
        allocated_port = (prov.details or {}).get("allocated_port")
    else:
        allocated_port = None

    if result["success"]:
        print(f"[nofal] CREATE_ACCOUNT OK username={username!r}", flush=True)
        db.add(
            ActivityLog(
                user_id=admin.id,
                action="CREATE_ACCOUNT",
                description=f"Created account for {username} ({domain}) port={allocated_port or '-'}",
                ip_address=request.client.host,
                status="success",
            )
        )
        db.commit()
        return RedirectResponse(url=f"/admin/accounts?success=Account+{username}+created", status_code=302)

    print(f"[nofal] CREATE_ACCOUNT FAIL username={username!r} err={result.get('error')!r}", flush=True)
    db.delete(new_user)
    db.add(
        ActivityLog(
            user_id=admin.id,
            action="CREATE_ACCOUNT",
            description=f"Failed for {username} ({domain}): {result.get('error', 'Unknown error')}",
            ip_address=request.client.host,
            status="error",
        )
    )
    db.commit()
    return templates.TemplateResponse(
        "admin/accounts_create.html",
        {
            "request": request,
            "user": admin,
            "packages": packages,
            "error": f"Server setup failed: {result.get('error', 'Unknown error')}",
            "steps": result.get("steps", {}),
        },
    )


@router.post("/accounts/{user_id}/suspend")
async def suspend_account(user_id: int, reason: str = Form(""), db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_suspended = True
    account.suspend_reason = reason
    AccountManager.suspend_account(account.username)

    log = ActivityLog(user_id=admin.id, action="SUSPEND_ACCOUNT",
                      description=f"Suspended {account.username}: {reason}",
                      ip_address="system", status="success")
    db.add(log)
    db.commit()
    return RedirectResponse(url="/admin/accounts?success=Account+suspended", status_code=302)


@router.post("/accounts/{user_id}/unsuspend")
async def unsuspend_account(user_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_suspended = False
    account.suspend_reason = None
    AccountManager.unsuspend_account(account.username)

    log = ActivityLog(user_id=admin.id, action="UNSUSPEND_ACCOUNT",
                      description=f"Unsuspended {account.username}",
                      ip_address="system", status="success")
    db.add(log)
    db.commit()
    return RedirectResponse(url="/admin/accounts?success=Account+unsuspended", status_code=302)


@router.post("/accounts/{user_id}/terminate")
async def terminate_account(user_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Remove server resources
    AccountProvisioningService.terminate_account(db, user=account)

    username = account.username
    db.delete(account)

    log = ActivityLog(user_id=admin.id, action="TERMINATE_ACCOUNT",
                      description=f"Terminated account: {username}",
                      ip_address="system", status="success")
    db.add(log)
    db.commit()
    return RedirectResponse(url="/admin/accounts?success=Account+terminated", status_code=302)


@router.get("/accounts/{user_id}/edit", response_class=HTMLResponse)
async def edit_account_page(user_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    account = db.query(User).filter(User.id == user_id).first()
    packages = db.query(Package).filter(Package.is_active == True).all()
    if not account:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin/accounts_edit.html", {
        "request": request, "user": admin, "account": account, "packages": packages, "page": "accounts"
    })


@router.post("/accounts/{user_id}/edit")
async def edit_account(
    user_id: int, request: Request,
    email: str = Form(...),
    package_id: int = Form(...),
    disk_quota_mb: int = Form(...),
    bandwidth_limit_mb: int = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    company: str = Form(""),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404)

    account.email = email
    account.package_id = package_id
    account.disk_quota_mb = disk_quota_mb
    account.bandwidth_limit_mb = bandwidth_limit_mb
    account.first_name = first_name
    account.last_name = last_name
    account.company = company
    db.commit()

    return RedirectResponse(url=f"/admin/accounts?success=Account+updated", status_code=302)


@router.get("/accounts/{user_id}/login-as")
async def login_as_user(user_id: int, request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    """Admin: login as a cPanel user (ghost login)"""
    from app.auth import create_access_token
    account = db.query(User).filter(User.id == user_id).first()
    if not account:
        raise HTTPException(status_code=404)

    token = create_access_token({"sub": account.username, "role": account.role, "user_id": account.id, "ghost": True})
    response = RedirectResponse(url="/cpanel/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=3600, samesite="lax")
    return response
