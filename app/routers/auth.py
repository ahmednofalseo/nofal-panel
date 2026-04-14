from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from app.templating import templates
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.config import settings
from app.auth import verify_password, create_access_token, get_password_hash
from app.models.user import User
from app.models.activity_log import ActivityLog

router = APIRouter(prefix="/auth", tags=["auth"])

def _public_url(request: Request, port: int) -> str:
    scheme = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    host = (request.headers.get("x-forwarded-host") or request.url.hostname or "").split(",")[0].strip()
    return f"{scheme}://{host}:{port}"


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    token = request.cookies.get("access_token")
    if token:
        from app.auth import decode_token
        payload = decode_token(token)
        if payload:
            user_role = payload.get("role", "user")
            if user_role == "admin":
                if settings.APP_MODE == "user":
                    return RedirectResponse(url=_public_url(request, settings.ADMIN_PUBLIC_PORT), status_code=302)
                return RedirectResponse(url="/admin/dashboard", status_code=302)
            if settings.APP_MODE == "admin":
                return RedirectResponse(url=_public_url(request, settings.USER_PUBLIC_PORT), status_code=302)
            return RedirectResponse(url="/cpanel/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    client_ip = request.client.host

    if not user or not verify_password(password, user.hashed_password):
        log = ActivityLog(action="LOGIN_FAILED", description=f"Failed login attempt for '{username}'",
                          ip_address=client_ip, status="failed")
        db.add(log)
        db.commit()
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Invalid username or password"
        })

    if user.is_suspended:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": f"Account suspended: {user.suspend_reason or 'Contact admin'}"
        })

    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Account is inactive. Contact admin."
        })

    # Create token
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})

    # Update last login
    user.last_login = datetime.utcnow()
    log = ActivityLog(user_id=user.id, action="LOGIN", description=f"User logged in",
                      ip_address=client_ip, status="success")
    db.add(log)
    db.commit()

    # Redirect based on role
    if user.role == "admin":
        redirect_url = _public_url(request, settings.ADMIN_PUBLIC_PORT) if settings.APP_MODE == "user" else "/admin/dashboard"
    else:
        redirect_url = _public_url(request, settings.USER_PUBLIC_PORT) if settings.APP_MODE == "admin" else "/cpanel/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, db: Session = Depends(get_db)):
    from app.auth import get_current_user_from_cookie
    try:
        user = get_current_user_from_cookie(request, db)
    except:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("change_password.html", {"request": request, "user": user})


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    from app.auth import get_current_user_from_cookie
    try:
        user = get_current_user_from_cookie(request, db)
    except:
        return RedirectResponse(url="/auth/login", status_code=302)

    if not verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "Current password is incorrect"
        })

    if new_password != confirm_password:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "New passwords do not match"
        })

    if len(new_password) < 8:
        return templates.TemplateResponse("change_password.html", {
            "request": request, "user": user, "error": "Password must be at least 8 characters"
        })

    user.hashed_password = get_password_hash(new_password)
    db.commit()

    return templates.TemplateResponse("change_password.html", {
        "request": request, "user": user, "success": "Password changed successfully!"
    })
