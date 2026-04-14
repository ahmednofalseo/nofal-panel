"""
Admin DNS Router - DNS Zone Management (WHM DNS Functions)
"""
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_admin_user
from app.models.domain import Domain, DNSRecord
from app.services.bind9 import DNSService

router = APIRouter(prefix="/admin", tags=["admin-dns"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dns", response_class=HTMLResponse)
async def dns_zones(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    domains = db.query(Domain).all()
    return templates.TemplateResponse("admin/dns.html", {
        "request": request, "user": admin, "domains": domains, "page": "dns"
    })


@router.get("/dns/{domain_name}/edit", response_class=HTMLResponse)
async def dns_editor(domain_name: str, request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    domain = db.query(Domain).filter(Domain.domain_name == domain_name).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    records = db.query(DNSRecord).filter(DNSRecord.domain_id == domain.id).all()
    zone_records = DNSService.get_zone_records(domain_name)
    zone_check = DNSService.check_zone(domain_name)

    return templates.TemplateResponse("admin/dns_editor.html", {
        "request": request, "user": admin,
        "domain": domain, "records": records,
        "zone_records": zone_records, "zone_check": zone_check,
        "page": "dns"
    })


@router.post("/dns/{domain_name}/add-record")
async def add_dns_record(
    domain_name: str, request: Request,
    record_type: str = Form(...),
    name: str = Form(...),
    value: str = Form(...),
    ttl: int = Form(3600),
    priority: int = Form(0),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    domain = db.query(Domain).filter(Domain.domain_name == domain_name).first()
    if not domain:
        raise HTTPException(status_code=404)

    # Save to DB
    record = DNSRecord(
        domain_id=domain.id, record_type=record_type,
        name=name, value=value, ttl=ttl, priority=priority
    )
    db.add(record)
    db.commit()

    # Add to zone file
    result = DNSService.add_record(domain_name, record_type, name, value, ttl, priority)

    return RedirectResponse(url=f"/admin/dns/{domain_name}/edit?success=Record+added", status_code=302)


@router.post("/dns/{domain_name}/delete-record/{record_id}")
async def delete_dns_record(
    domain_name: str, record_id: int,
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    record = db.query(DNSRecord).filter(DNSRecord.id == record_id).first()
    if record:
        DNSService.delete_record(domain_name, record.record_type, record.name, record.value)
        db.delete(record)
        db.commit()
    return RedirectResponse(url=f"/admin/dns/{domain_name}/edit?success=Record+deleted", status_code=302)


@router.post("/dns/{domain_name}/reload")
async def reload_zone(domain_name: str, admin=Depends(get_admin_user)):
    result = DNSService.reload()
    return JSONResponse(result)


@router.get("/dns/{domain_name}/check")
async def check_zone(domain_name: str, admin=Depends(get_admin_user)):
    result = DNSService.check_zone(domain_name)
    return JSONResponse(result)
