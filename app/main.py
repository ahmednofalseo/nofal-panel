"""
NOFAL PANEL - Main FastAPI Application
A WHM/cPanel-like hosting control panel
"""
from __future__ import annotations

import platform
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn

from app.config import settings
from app.paths import STATIC_DIR
from app.templating import templates
from app.database import init_db, SessionLocal
from app.auth import get_password_hash
from app.security import CSRF_COOKIE_NAME, generate_csrf_token, get_csrf_cookie, get_csrf_header, is_csrf_exempt
from app.helpers.public_url import public_panel_path

def create_app() -> FastAPI:
    """Create an app instance according to settings.APP_MODE."""
    mode = settings.APP_MODE or "full"

    app = FastAPI(
        title="Nofal Panel",
        description="WHM/cPanel-like Hosting Control Panel",
        version=settings.PANEL_VERSION,
        docs_url=None,
        redoc_url=None,
    )

    # Static files must be absolute (systemd cwd-safe)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # Routers
    from app.routers import auth
    from app.routers import status as status_router
    from app.routers import health as health_router

    app.include_router(auth.router)
    app.include_router(status_router.router)
    app.include_router(health_router.router)

    if mode in ("full", "admin"):
        from app.routers.admin import accounts, packages, server, dns, analytics, plugins
        app.include_router(accounts.router)
        app.include_router(packages.router)
        app.include_router(server.router)
        app.include_router(dns.router)
        app.include_router(analytics.router)
        app.include_router(plugins.router)

        # Plugin routes (enabled only). Safe to no-op if DB not ready.
        try:
            from pathlib import Path
            from app.services.plugins import PluginManager

            plugins_dir = Path(__file__).resolve().parents[1] / "plugins"
            pm = PluginManager(plugins_dir=plugins_dir)
            with SessionLocal() as db:
                pm.mount_enabled(app, db)
        except Exception:
            pass

    if mode in ("full", "user"):
        from app.routers.cpanel import dashboard, email, domains, databases, ftp, ssl, cron, files, terminal, features
        app.include_router(dashboard.router)
        app.include_router(email.router)
        app.include_router(domains.router)
        app.include_router(databases.router)
        app.include_router(ftp.router)
        app.include_router(ssl.router)
        app.include_router(cron.router)
        app.include_router(files.router)
        app.include_router(terminal.router)
        app.include_router(features.router)

    @app.middleware("http")
    async def runtime_notice_middleware(request: Request, call_next):
        """Warn on non-Linux hosts: WHM service control expects Ubuntu/Debian."""
        request.state.whm_runtime_notice = None
        if platform.system() != "Linux":
            request.state.whm_runtime_notice = (
                "هذا الجهاز ليس Linux. أوامر WHM الحقيقية (systemctl، UFW، BIND، …) "
                "تعمل على Ubuntu/Debian على الخادم. الواجهة تعرض البيانات المحلية المتاحة فقط."
            )
        response = await call_next(request)

        # Ensure CSRF cookie exists for browser sessions.
        if not request.cookies.get(CSRF_COOKIE_NAME):
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=generate_csrf_token(),
                httponly=False,
                samesite="lax",
                secure=False,  # set True when serving HTTPS end-to-end
                max_age=60 * 60 * 24 * 7,
            )
        return response

    @app.middleware("http")
    async def csrf_protect_middleware(request: Request, call_next):
        # Protect state-changing requests for browser UI.
        if request.method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            if is_csrf_exempt(request):
                return await call_next(request)
            cookie_token = get_csrf_cookie(request)
            header_token = get_csrf_header(request)

            form_token = None
            try:
                # Read body safely for form parsing without breaking handlers.
                body = await request.body()
                request._body = body  # type: ignore[attr-defined]
                if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") or "multipart/form-data" in request.headers.get("content-type", ""):
                    form = await request.form()
                    form_token = form.get("csrf_token") if form else None
                request._body = body  # type: ignore[attr-defined]
            except Exception:
                # If parsing fails, rely on header token.
                pass

            provided = header_token or form_token
            if not cookie_token or not provided or provided != cookie_token:
                return templates.TemplateResponse("errors/403.html", {"request": request}, status_code=403)

        return await call_next(request)

    @app.get("/")
    async def root(request: Request):
        token = request.cookies.get("access_token")
        if token:
            from app.auth import decode_token
            payload = decode_token(token)
            if payload:
                role = payload.get("role", "user")
                if role == "admin":
                    if mode == "user":
                        return RedirectResponse(
                            url=public_panel_path(request, settings.ADMIN_PUBLIC_PORT, "/admin/dashboard"),
                            status_code=302,
                        )
                    return RedirectResponse(url="/admin/dashboard", status_code=302)
                # user
                if mode == "admin":
                    return RedirectResponse(
                        url=public_panel_path(request, settings.USER_PUBLIC_PORT, "/cpanel/dashboard"),
                        status_code=302,
                    )
                return RedirectResponse(url="/cpanel/dashboard", status_code=302)
        return RedirectResponse(url="/auth/login", status_code=302)

    # Startup: Initialize DB + Admin User
    @app.on_event("startup")
    async def startup_event():
        print(f"[START] Starting {settings.PANEL_NAME} v{settings.PANEL_VERSION} ({mode})...")
        init_db()

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
                        bandwidth_limit_mb=0,
                        email_limit=0,
                        db_limit=0,
                        ftp_limit=0,
                        subdomain_limit=0,
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
        finally:
            db.close()

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
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

    return app


app = create_app()


# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.PANEL_HOST,
        port=settings.PANEL_PORT,
        reload=False,
        workers=2,
    )
