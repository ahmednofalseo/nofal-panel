from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import get_admin_user
from app.database import get_db
from app.models.user import User
from app.services.analytics import AnalyticsService
from app.templating import templates


router = APIRouter(prefix="/admin", tags=["admin-analytics"])


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    users = db.query(User).filter(User.role != "admin").all()

    usage = []
    for u in users:
        disk = AnalyticsService.disk_usage_mb(u.username)
        files = AnalyticsService.file_count(u.username)
        usage.append({"user": u, "disk_mb": disk, "file_count": files})

        # persist latest disk usage for dashboard insights
        u.disk_used_mb = disk

    db.commit()

    top_disk = sorted(usage, key=lambda x: x["disk_mb"], reverse=True)[:10]
    top_files = sorted(usage, key=lambda x: x["file_count"], reverse=True)[:10]

    return templates.TemplateResponse(
        "admin/analytics.html",
        {
            "request": request,
            "user": admin,
            "page": "analytics",
            "top_disk": top_disk,
            "top_files": top_files,
        },
    )

