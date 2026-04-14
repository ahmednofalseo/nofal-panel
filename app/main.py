"""
NOFAL PANEL - Main FastAPI Application
A WHM/cPanel-like hosting control panel
"""
import platform
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn

from app.config import settings
from app.database import init_db, get_db, SessionLocal
from app.auth import get_password_hash

# ─── Create FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title="Nofal Panel",
    description="WHM/cPanel-like Hosting Control Panel",
    version=settings.PANEL_VERSION,
    docs_url=None,
    redoc_url=None,
)

# ─── Static Files ─────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── Templates ────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="app/templates")

# ─── Include Routers ─────────────────────────────────────────────────────────
from app.routers import auth
from app.routers.admin import accounts, packages, server, dns
from app.routers.cpanel import dashboard, email, domains, databases, ftp, ssl, cron, files, terminal
from app.routers import status as status_router

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(packages.router)
app.include_router(server.router)
app.include_router(dns.router)
app.include_router(dashboard.router)
app.include_router(email.router)
app.include_router(domains.router)
app.include_router(databases.router)
app.include_router(ftp.router)
app.include_router(ssl.router)
app.include_router(cron.router)
app.include_router(files.router)
app.include_router(terminal.router)
app.include_router(status_router.router)


@app.middleware("http")
async def runtime_notice_middleware(request: Request, call_next):
    """Warn on non-Linux hosts: WHM service control expects Ubuntu/Debian."""
    request.state.whm_runtime_notice = None
    if platform.system() != "Linux":
        request.state.whm_runtime_notice = (
            "هذا الجهاز ليس Linux. أوامر WHM الحقيقية (systemctl، UFW، BIND، …) "
            "تعمل على Ubuntu/Debian على الخادم. الواجهة تعرض البيانات المحلية المتاحة فقط."
        )
    return await call_next(request)


# ─── Root Redirect ────────────────────────────────────────────────────────────
@app.get("/")
async def root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        from app.auth import decode_token
        payload = decode_token(token)
        if payload:
            role = payload.get("role", "user")
            return RedirectResponse(url="/admin/dashboard" if role == "admin" else "/cpanel/dashboard")
    return RedirectResponse(url="/auth/login")


# ─── Startup: Initialize DB + Admin User ─────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    print(f"[START] Starting {settings.PANEL_NAME} v{settings.PANEL_VERSION}...")

    # Initialize database tables
    init_db()

    # Create default admin user if not exists
    db = SessionLocal()
    try:
        from app.models.user import User
        from app.models.package import Package

        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            admin_user = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                first_name="Admin",
                last_name="User",
            )
            db.add(admin_user)
            print(f"[OK] Admin user created: {settings.ADMIN_USERNAME}")

        # Create default packages
        if db.query(Package).count() == 0:
            packages_data = [
                Package(
                    name="Starter",
                    description="Basic hosting package",
                    disk_quota_mb=1024,
                    bandwidth_limit_mb=10240,
                    email_limit=5,
                    db_limit=3,
                    ftp_limit=2,
                    subdomain_limit=5,
                    addon_domain_limit=1,
                    price_monthly=5.99,
                    is_active=True,
                    is_default=True,
                ),
                Package(
                    name="Business",
                    description="Professional hosting package",
                    disk_quota_mb=5120,
                    bandwidth_limit_mb=51200,
                    email_limit=25,
                    db_limit=10,
                    ftp_limit=10,
                    subdomain_limit=20,
                    addon_domain_limit=5,
                    has_ssh=True,
                    price_monthly=14.99,
                    is_active=True,
                ),
                Package(
                    name="Pro",
                    description="Premium unlimited hosting",
                    disk_quota_mb=20480,
                    bandwidth_limit_mb=0,  # Unlimited
                    email_limit=0,         # Unlimited
                    db_limit=0,            # Unlimited
                    ftp_limit=0,           # Unlimited
                    subdomain_limit=0,     # Unlimited
                    addon_domain_limit=10,
                    has_ssh=True,
                    has_softaculous=True,
                    price_monthly=29.99,
                    is_active=True,
                ),
            ]
            for pkg in packages_data:
                db.add(pkg)
            print("[OK] Default packages created (Starter, Business, Pro)")

        db.commit()
        print(f"[OK] {settings.PANEL_NAME} is ready!")
        print(f"[WEB] Access at: http://0.0.0.0:{settings.PANEL_PORT}")
        print(f"[USER] Admin: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")

    finally:
        db.close()


# ─── Error Handlers ───────────────────────────────────────────────────────────
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Honor Location on redirects; HTML errors; covers Starlette 404 + FastAPI HTTPException."""
    loc = None
    if exc.headers:
        loc = exc.headers.get("Location") or exc.headers.get("location")
    if loc and exc.status_code in (301, 302, 303, 307, 308):
        return RedirectResponse(url=loc, status_code=exc.status_code)
    if exc.status_code == 403:
        return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)
    if exc.status_code == 404:
        return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.PANEL_HOST,
        port=settings.PANEL_PORT,
        reload=False,
        workers=2,
    )
