from __future__ import annotations

from fastapi import APIRouter


def get_router() -> APIRouter:
    router = APIRouter()

    @router.get("/")
    async def index():
        return {"plugin": "hello", "ok": True}

    return router


def register(event_bus) -> None:
    # Example hook; no-op for now.
    event_bus.on("onLogin", lambda payload: None)

