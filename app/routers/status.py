"""
Operational status page + JSON API (requires login).
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user_from_cookie
from app.status_registry import REGISTRY, counts_by_status

router = APIRouter(tags=["status"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/status", response_class=HTMLResponse)
async def panel_status_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "user": user,
            "rows": REGISTRY,
            "counts": counts_by_status(),
            "page": "status",
        },
    )


@router.get("/api/status")
async def panel_status_api(request: Request, db: Session = Depends(get_db)):
    get_current_user_from_cookie(request, db)
    return JSONResponse(
        {
            "version": "1.0.0",
            "counts": counts_by_status(),
            "items": REGISTRY,
        }
    )
