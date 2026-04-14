from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database import SessionLocal


router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz():
    # Lightweight DB check.
    try:
        with SessionLocal() as db:
            db.execute("SELECT 1")
        return JSONResponse({"ok": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)

