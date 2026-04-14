from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import Session

from app.models.plugin import Plugin


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list] = {}

    def on(self, event: str, handler) -> None:
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        for h in self._handlers.get(event, []):
            try:
                h(payload)
            except Exception:
                continue


class PluginModule(Protocol):
    def get_router(self) -> APIRouter: ...
    def register(self, event_bus: EventBus) -> None: ...


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    module: str  # import path, e.g. "plugins.hello.plugin"


class PluginManager:
    def __init__(self, plugins_dir: Path) -> None:
        self.plugins_dir = plugins_dir
        self.event_bus = EventBus()

    def discover_manifests(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not self.plugins_dir.exists():
            return manifests
        for p in sorted(self.plugins_dir.iterdir()):
            if not p.is_dir():
                continue
            mf = p / "manifest.json"
            if not mf.exists():
                continue
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                manifests.append(
                    PluginManifest(
                        name=str(data["name"]),
                        version=str(data.get("version") or "0.0.0"),
                        module=str(data["module"]),
                    )
                )
            except Exception:
                continue
        return manifests

    def sync_db(self, db: Session) -> None:
        existing = {p.name: p for p in db.query(Plugin).all()}
        for mf in self.discover_manifests():
            if mf.name not in existing:
                db.add(Plugin(name=mf.name, version=mf.version, enabled=False))
            else:
                existing[mf.name].version = mf.version
        db.commit()

    def mount_enabled(self, app: FastAPI, db: Session) -> dict[str, Any]:
        self.sync_db(db)
        enabled = db.query(Plugin).filter(Plugin.enabled == True).all()  # noqa: E712
        mounted: list[str] = []
        errors: list[dict[str, str]] = []
        manifests_by_name = {m.name: m for m in self.discover_manifests()}
        for p in enabled:
            try:
                mf = manifests_by_name.get(p.name)
                if not mf:
                    raise RuntimeError("manifest.json not found")
                module = importlib.import_module(mf.module)
                router = getattr(module, "get_router")()
                app.include_router(router, prefix=f"/plugins/{p.name}", tags=[f"plugin:{p.name}"])
                # optional hooks
                reg = getattr(module, "register", None)
                if callable(reg):
                    reg(self.event_bus)
                mounted.append(p.name)
            except Exception as exc:
                errors.append({"plugin": p.name, "error": str(exc)})
        return {"mounted": mounted, "errors": errors}

