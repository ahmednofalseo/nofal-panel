"""
cPanel Domains Router - Domain, Subdomain, Addon, Parked, Redirects
"""
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_cpanel_user
from app.models.domain import Domain
from app.services.nginx import NginxService
from app.services.bind9 import DNSService
from app.config import settings

router = APIRouter(prefix="/cpanel", tags=["cpanel-domains"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/domains", response_class=HTMLResponse)
async def domains_page(request: Request, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    domains = db.query(Domain).filter(Domain.user_id == user.id).order_by(Domain.domain_name).all()
    main_domain = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type == "main").first()
    server_ip = (settings.PANEL_PUBLIC_IP or user.ip_address or "").strip() or "—"
    return templates.TemplateResponse(
        "cpanel/domains.html",
        {
            "request": request,
            "user": user,
            "domains": domains,
            "main_domain": main_domain,
            "page": "domains",
            "server_ip": server_ip,
        },
    )


@router.post("/domains/add-addon")
async def add_addon_domain(
    request: Request,
    domain_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    # Check limit
    addon_count = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type == "addon").count()
    if user.addon_domain_limit > 0 and addon_count >= user.addon_domain_limit:
        return RedirectResponse(url="/cpanel/domains?error=Addon+domain+limit+reached", status_code=302)

    doc_root = f"{settings.ACCOUNTS_HOME}/{user.username}/public_html/{domain_name}"
    result = NginxService.create_vhost(username=user.username, domain=domain_name, document_root=doc_root)

    if result["success"]:
        domain = Domain(
            user_id=user.id, domain_name=domain_name,
            domain_type="addon", document_root=doc_root,
            ip_address=user.ip_address
        )
        db.add(domain)
        db.commit()
        DNSService.create_zone(domain_name, user.ip_address or "127.0.0.1")
        return RedirectResponse(url="/cpanel/domains?success=Addon+domain+added", status_code=302)

    return RedirectResponse(url=f"/cpanel/domains?error={result.get('error', 'Failed')}", status_code=302)


@router.post("/domains/add-subdomain")
async def add_subdomain(
    request: Request,
    subdomain: str = Form(...),
    parent_domain: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    sub_count = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type == "subdomain").count()
    if user.subdomain_limit > 0 and sub_count >= user.subdomain_limit:
        return RedirectResponse(url="/cpanel/domains?error=Subdomain+limit+reached", status_code=302)

    full_domain = f"{subdomain}.{parent_domain}"
    doc_root = f"{settings.ACCOUNTS_HOME}/{user.username}/public_html/{subdomain}.{parent_domain}"
    result = NginxService.add_subdomain(user.username, subdomain, parent_domain, doc_root)

    if result["success"]:
        domain = Domain(
            user_id=user.id, domain_name=full_domain,
            domain_type="subdomain", document_root=doc_root,
            ip_address=user.ip_address
        )
        db.add(domain)
        db.commit()
        DNSService.add_record(parent_domain, "A", subdomain, user.ip_address or "127.0.0.1")
        return RedirectResponse(url="/cpanel/domains?success=Subdomain+added", status_code=302)

    return RedirectResponse(url=f"/cpanel/domains?error=Failed+to+create+subdomain", status_code=302)


@router.post("/domains/add-parked")
async def add_parked_domain(
    domain_name: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    parked_count = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type == "parked").count()
    if user.parked_domain_limit > 0 and parked_count >= user.parked_domain_limit:
        return RedirectResponse(url="/cpanel/domains?error=Parked+domain+limit+reached", status_code=302)

    main_domain = db.query(Domain).filter(Domain.user_id == user.id, Domain.domain_type == "main").first()
    doc_root = main_domain.document_root if main_domain else f"{settings.ACCOUNTS_HOME}/{user.username}/public_html"

    result = NginxService.create_vhost(username=user.username, domain=domain_name, document_root=doc_root)
    if result["success"]:
        domain = Domain(
            user_id=user.id, domain_name=domain_name,
            domain_type="parked", document_root=doc_root,
            ip_address=user.ip_address
        )
        db.add(domain)
        db.commit()
        return RedirectResponse(url="/cpanel/domains?success=Parked+domain+added", status_code=302)

    return RedirectResponse(url="/cpanel/domains?error=Failed", status_code=302)


@router.post("/domains/add-redirect")
async def add_redirect(
    domain_name: str = Form(...),
    redirect_to: str = Form(...),
    redirect_type: str = Form("301"),
    db: Session = Depends(get_db),
    user=Depends(get_cpanel_user)
):
    domain = Domain(
        user_id=user.id, domain_name=domain_name,
        domain_type="redirect", redirect_to=redirect_to,
        redirect_type=redirect_type, ip_address=user.ip_address
    )
    db.add(domain)
    db.commit()
    return RedirectResponse(url="/cpanel/domains?success=Redirect+added", status_code=302)


@router.post("/domains/{domain_id}/delete")
async def delete_domain(domain_id: int, db: Session = Depends(get_db), user=Depends(get_cpanel_user)):
    domain = db.query(Domain).filter(Domain.id == domain_id, Domain.user_id == user.id).first()
    if domain and domain.domain_type != "main":
        NginxService.delete_vhost(domain.domain_name)
        db.delete(domain)
        db.commit()
    return RedirectResponse(url="/cpanel/domains?success=Domain+removed", status_code=302)
