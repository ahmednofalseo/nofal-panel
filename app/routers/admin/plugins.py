from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_admin_user
from app.database import get_db
from app.models.plugin import Plugin
from app.services.plugins import PluginManager
from app.templating import templates


router = APIRouter(prefix="/admin", tags=["admin-plugins"])


@router.get("/plugins", response_class=HTMLResponse)
async def plugins_page(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    pm = PluginManager(plugins_dir=Path(__file__).resolve().parents[3] / "plugins")
    pm.sync_db(db)
    plugins = db.query(Plugin).order_by(Plugin.name.asc()).all()
    return templates.TemplateResponse(
        "admin/plugins.html",
        {"request": request, "user": admin, "plugins": plugins, "page": "plugins"},
    )


@router.post("/plugins/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    p = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if p:
        p.enabled = not bool(p.enabled)
        db.commit()
    return RedirectResponse(url="/admin/plugins?success=Plugin+updated", status_code=302)

