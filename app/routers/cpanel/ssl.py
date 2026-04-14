"""cPanel SSL Router - SSL Certificate Management"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.models.ssl_cert import SSLCert
from app.models.domain import Domain
from app.services.certbot import SSLService
from app.services.nginx import NginxService
from app.templating import templates

router = APIRouter(prefix="/cpanel", tags=["cpanel-ssl"])


@router.get("/ssl", response_class=HTMLResponse)
async def ssl_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    certs = db.query(SSLCert).filter(SSLCert.user_id == user.id).all()
    domains = db.query(Domain).filter(Domain.user_id == user.id).all()
    all_certs = SSLService.list_certificates()
    return templates.TemplateResponse("cpanel/ssl.html", {
        "request": request, "user": user,
        "certs": certs, "domains": domains,
        "all_certs": all_certs, "page": "ssl"
    })


@router.post("/ssl/issue")
async def issue_ssl(
    domain_name: str = Form(...),
    cert_type: str = Form("letsencrypt"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    domain = db.query(Domain).filter(Domain.domain_name == domain_name, Domain.user_id == user.id).first()
    if not domain:
        return RedirectResponse(url="/cpanel/ssl?error=Domain+not+found", status_code=302)

    if cert_type == "letsencrypt":
        result = SSLService.issue_letsencrypt(domain_name, webroot=domain.document_root)
    else:
        result = SSLService.create_self_signed(domain_name)

    if result["success"]:
        # Enable SSL in Nginx
        NginxService.enable_ssl(
            domain=domain_name,
            cert_path=result["cert_path"],
            key_path=result["key_path"],
            username=user.username
        )

        domain.has_ssl = True
        cert = SSLCert(
            user_id=user.id, domain=domain_name,
            cert_type=cert_type,
            cert_path=result.get("cert_path"),
            key_path=result.get("key_path"),
        )
        db.add(cert)
        db.commit()
        return RedirectResponse(url="/cpanel/ssl?success=SSL+certificate+issued", status_code=302)

    return RedirectResponse(url=f"/cpanel/ssl?error={result.get('error', 'Failed')}", status_code=302)


@router.post("/ssl/{cert_id}/renew")
async def renew_ssl(cert_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cert = db.query(SSLCert).filter(SSLCert.id == cert_id, SSLCert.user_id == user.id).first()
    if cert:
        result = SSLService.renew_certificate(cert.domain)
        if result["success"]:
            return RedirectResponse(url="/cpanel/ssl?success=Certificate+renewed", status_code=302)
    return RedirectResponse(url="/cpanel/ssl?error=Renewal+failed", status_code=302)


@router.post("/ssl/{cert_id}/delete")
async def delete_ssl(cert_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    cert = db.query(SSLCert).filter(SSLCert.id == cert_id, SSLCert.user_id == user.id).first()
    if cert:
        SSLService.revoke_certificate(cert.domain)
        db.delete(cert)
        db.commit()
    return RedirectResponse(url="/cpanel/ssl?success=Certificate+deleted", status_code=302)
