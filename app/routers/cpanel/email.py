"""
cPanel Email Router - Email Account Management
"""
from urllib.parse import quote, quote_plus

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_cpanel_user, get_password_hash
from app.config import settings
from app.database import get_db
from app.models.domain import Domain
from app.models.email_account import EmailAccount
from app.services.postfix import MailService

router = APIRouter(prefix="/cpanel", tags=["cpanel-email"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["urlq"] = lambda s: quote(str(s), safe="")


def _mail_hosts(request: Request) -> dict:
    """IMAP/SMTP hostnames shown to the user (env or same host as the panel)."""
    host = (request.url.hostname or "").strip() or "localhost"
    imap = (settings.MAIL_IMAP_HOST or "").strip() or host
    smtp = (settings.MAIL_SMTP_HOST or "").strip() or host
    return {
        "imap_host": imap,
        "smtp_host": smtp,
        "imap_port": settings.MAIL_IMAP_PORT,
        "smtp_port": settings.MAIL_SMTP_PORT,
        "smtp_port_ssl": settings.MAIL_SMTP_PORT_SSL,
        "webmail_url": (settings.WEBMAIL_URL or "").rstrip("/"),
    }


def _domain_choices(db: Session, user) -> list:
    rows = (
        db.query(Domain)
        .filter(Domain.user_id == user.id, Domain.domain_type.in_(["main", "addon"]))
        .order_by(Domain.domain_name)
        .all()
    )
    names = [d.domain_name for d in rows]
    if not names and (user.primary_domain or "").strip():
        names = [user.primary_domain.strip()]
    return names


@router.get("/email", response_class=HTMLResponse)
async def email_accounts(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    emails = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).order_by(EmailAccount.email).all()
    domain_options = _domain_choices(db, user)
    mail_hosts = _mail_hosts(request)
    mail_ready = MailService.system_ready()
    svc = MailService.get_service_status() if mail_ready else {"postfix": "—", "dovecot": "—"}
    limit = user.email_limit if user.email_limit and user.email_limit > 0 else None
    return templates.TemplateResponse(
        "cpanel/email.html",
        {
            "request": request,
            "user": user,
            "emails": emails,
            "domain_options": domain_options,
            "email_count": len(emails),
            "email_limit": limit,
            "page": "email",
            "mail_hosts": mail_hosts,
            "mail_system_ready": mail_ready,
            "mail_services": svc,
        },
    )


@router.get("/email/open-webmail", response_class=HTMLResponse)
async def open_webmail(
    request: Request,
    account: str,
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    """Redirect to Roundcube/SOGo etc. with mailbox prefilled (_user)."""
    account = (account or "").strip()
    if not account or "@" not in account:
        return RedirectResponse(url="/cpanel/email?error=Invalid+account", status_code=302)
    row = (
        db.query(EmailAccount)
        .filter(EmailAccount.user_id == user.id, EmailAccount.email == account)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404)
    base = (settings.WEBMAIL_URL or "").rstrip("/")
    if not base:
        return RedirectResponse(url="/cpanel/email?error=Webmail+URL+not+set+in+env", status_code=302)
    sep = "&" if "?" in base else "?"
    target = f"{base}{sep}_user={quote(account)}"
    return RedirectResponse(url=target, status_code=302)


@router.post("/email/create")
async def create_email(
    request: Request,
    email_user: str = Form(...),
    email_domain: str = Form(...),
    password: str = Form(...),
    quota_mb: int = Form(1024),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    email_user = email_user.strip().lower()[:80]
    email_domain = email_domain.strip().lower()[:255]
    if not email_user or not email_domain:
        return RedirectResponse(url="/cpanel/email?error=Invalid+mailbox+name", status_code=302)

    current_count = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).count()
    if user.email_limit > 0 and current_count >= user.email_limit:
        return RedirectResponse(url="/cpanel/email?error=Email+limit+reached", status_code=302)

    full_email = f"{email_user}@{email_domain}"
    if db.query(EmailAccount).filter(EmailAccount.email == full_email).first():
        return RedirectResponse(url=f"/cpanel/email?error=Address+already+exists", status_code=302)

    allowed = set(_domain_choices(db, user))
    if email_domain not in allowed:
        return RedirectResponse(url="/cpanel/email?error=Domain+not+allowed", status_code=302)

    if len(password) < 8:
        return RedirectResponse(url="/cpanel/email?error=Password+min+8+chars", status_code=302)

    quota_mb = max(64, min(quota_mb, 102400))

    result = MailService.create_email_account(full_email, password, quota_mb)
    if not result.get("success"):
        err = quote_plus(result.get("error", "Mail server error")[:200])
        return RedirectResponse(url=f"/cpanel/email?error={err}", status_code=302)

    account = EmailAccount(
        user_id=user.id,
        email=full_email,
        username=email_user,
        domain=email_domain,
        hashed_password=get_password_hash(password),
        quota_mb=quota_mb,
    )
    db.add(account)
    db.commit()

    extra = "&mail_mode=panel" if result.get("panel_only") else "&mail_mode=server"
    return RedirectResponse(url=f"/cpanel/email?success=Mailbox+created{extra}", status_code=302)


@router.post("/email/{email_id}/delete")
async def delete_email(email_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    row = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if row:
        MailService.delete_email_account(row.email)
        db.delete(row)
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Mailbox+removed", status_code=302)


@router.post("/email/{email_id}/change-password")
async def change_email_password(
    email_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    row = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if not row:
        return RedirectResponse(url="/cpanel/email?error=Not+found", status_code=302)
    if len(new_password) < 8:
        return RedirectResponse(url="/cpanel/email?error=Password+min+8+chars", status_code=302)

    if MailService.system_ready():
        res = MailService.change_email_password(row.email, new_password)
        if not res.get("success"):
            e = quote_plus(res.get("error", "mail")[:200])
            return RedirectResponse(url=f"/cpanel/email?error={e}", status_code=302)

    row.hashed_password = get_password_hash(new_password)
    db.commit()
    return RedirectResponse(url="/cpanel/email?success=Password+updated", status_code=302)


@router.post("/email/{email_id}/forwarder")
async def create_forwarder(
    email_id: int,
    forward_to: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    row = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if row:
        MailService.create_forwarder(row.email, forward_to.strip())
        row.is_forwarder = bool(forward_to.strip())
        row.forward_to = forward_to.strip()[:500] or None
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Forwarder+saved", status_code=302)


@router.post("/email/{email_id}/autoresponder")
async def set_autoresponder(
    email_id: int,
    subject: str = Form(...),
    body: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user),
):
    row = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if row:
        row.has_autoresponder = True
        row.autoresponder_subject = subject[:255]
        row.autoresponder_body = body[:2000]
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Autoresponder+saved", status_code=302)
