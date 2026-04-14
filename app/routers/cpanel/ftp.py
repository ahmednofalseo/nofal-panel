"""cPanel FTP Router"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user, get_password_hash
from app.models.ftp_account import FtpAccount
from app.services.vsftpd import FTPService
from app.config import settings

router = APIRouter(prefix="/cpanel", tags=["cpanel-ftp"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/ftp", response_class=HTMLResponse)
async def ftp_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    accounts = db.query(FtpAccount).filter(FtpAccount.user_id == user.id).all()
    return templates.TemplateResponse("cpanel/ftp.html", {
        "request": request, "user": user, "accounts": accounts,
        "ftp_count": len(accounts), "page": "ftp"
    })


@router.post("/ftp/create")
async def create_ftp(
    username_suffix: str = Form(...),
    password: str = Form(...),
    home_dir: str = Form(""),
    quota_mb: int = Form(0),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    ftp_count = db.query(FtpAccount).filter(FtpAccount.user_id == user.id).count()
    if user.ftp_limit > 0 and ftp_count >= user.ftp_limit:
        return RedirectResponse(url="/cpanel/ftp?error=FTP+limit+reached", status_code=302)

    full_username = f"{user.username}_{username_suffix}"
    if not home_dir:
        home_dir = f"{settings.ACCOUNTS_HOME}/{user.username}/public_html"

    result = FTPService.create_ftp_account(full_username, password, home_dir, quota_mb)
    if result["success"]:
        account = FtpAccount(
            user_id=user.id, username=full_username,
            hashed_password=get_password_hash(password),
            home_directory=home_dir, quota_mb=quota_mb
        )
        db.add(account)
        db.commit()
        return RedirectResponse(url="/cpanel/ftp?success=FTP+account+created", status_code=302)

    return RedirectResponse(url=f"/cpanel/ftp?error=Failed+to+create+FTP+account", status_code=302)


@router.post("/ftp/{ftp_id}/delete")
async def delete_ftp(ftp_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    account = db.query(FtpAccount).filter(FtpAccount.id == ftp_id, FtpAccount.user_id == user.id).first()
    if account:
        FTPService.delete_ftp_account(account.username)
        db.delete(account)
        db.commit()
    return RedirectResponse(url="/cpanel/ftp?success=FTP+account+deleted", status_code=302)


@router.post("/ftp/{ftp_id}/change-password")
async def change_ftp_password(
    ftp_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    account = db.query(FtpAccount).filter(FtpAccount.id == ftp_id, FtpAccount.user_id == user.id).first()
    if account:
        FTPService.change_ftp_password(account.username, new_password)
        account.hashed_password = get_password_hash(new_password)
        db.commit()
    return RedirectResponse(url="/cpanel/ftp?success=Password+changed", status_code=302)
