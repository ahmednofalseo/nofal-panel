"""
cPanel Email Router - Email Account Management
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user, get_password_hash
from app.models.email_account import EmailAccount
from app.models.domain import Domain
from app.services.postfix import MailService

router = APIRouter(prefix="/cpanel", tags=["cpanel-email"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/email", response_class=HTMLResponse)
async def email_accounts(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    emails = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).all()
    domains = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type.in_(["main", "addon"])).all()
    return templates.TemplateResponse("cpanel/email.html", {
        "request": request, "user": user,
        "emails": emails, "domains": domains,
        "email_count": len(emails), "page": "email"
    })


@router.post("/email/create")
async def create_email(
    request: Request,
    email_user: str = Form(...),
    email_domain: str = Form(...),
    password: str = Form(...),
    quota_mb: int = Form(1024),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    # Check limit
    current_count = db.query(EmailAccount).filter(EmailAccount.user_id == user.id).count()
    if user.email_limit > 0 and current_count >= user.email_limit:
        return RedirectResponse(url="/cpanel/email?error=Email+limit+reached", status_code=302)

    full_email = f"{email_user}@{email_domain}"

    if db.query(EmailAccount).filter(EmailAccount.email == full_email).first():
        return RedirectResponse(url=f"/cpanel/email?error=Email+{full_email}+already+exists", status_code=302)

    # Create on mail server
    result = MailService.create_email_account(full_email, password, quota_mb)

    if result["success"]:
        account = EmailAccount(
            user_id=user.id, email=full_email,
            username=email_user, domain=email_domain,
            hashed_password=get_password_hash(password),
            quota_mb=quota_mb
        )
        db.add(account)
        db.commit()
        return RedirectResponse(url="/cpanel/email?success=Email+account+created", status_code=302)

    return RedirectResponse(url=f"/cpanel/email?error={result.get('error', 'Failed')}", status_code=302)


@router.post("/email/{email_id}/delete")
async def delete_email(email_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    email = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if email:
        MailService.delete_email_account(email.email)
        db.delete(email)
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Email+deleted", status_code=302)


@router.post("/email/{email_id}/change-password")
async def change_email_password(
    email_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    email = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if email:
        MailService.change_email_password(email.email, new_password)
        email.hashed_password = get_password_hash(new_password)
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Password+changed", status_code=302)


@router.post("/email/{email_id}/forwarder")
async def create_forwarder(
    email_id: int,
    forward_to: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    email = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if email:
        MailService.create_forwarder(email.email, forward_to)
        email.is_forwarder = True
        email.forward_to = forward_to
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Forwarder+created", status_code=302)


@router.post("/email/{email_id}/autoresponder")
async def set_autoresponder(
    email_id: int,
    subject: str = Form(...),
    body: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    email = db.query(EmailAccount).filter(EmailAccount.id == email_id, EmailAccount.user_id == user.id).first()
    if email:
        email.has_autoresponder = True
        email.autoresponder_subject = subject
        email.autoresponder_body = body
        db.commit()
    return RedirectResponse(url="/cpanel/email?success=Autoresponder+set", status_code=302)
