from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task

from app.database import SessionLocal
from app.models.user import User
from app.services.analytics import AnalyticsService
from app.services.bind9 import DNSService
from app.services.nginx import NginxService


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def reload_nginx(self) -> dict:
    test = NginxService.test_config()
    if not test.get("success"):
        raise RuntimeError(test.get("error") or "nginx test failed")
    return NginxService.reload()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5})
def reload_dns(self) -> dict:
    return DNSService.reload()


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def collect_disk_usage(self) -> dict:
    with SessionLocal() as db:
        users = db.query(User).filter(User.role != "admin").all()
        for u in users:
            u.disk_used_mb = AnalyticsService.disk_usage_mb(u.username)
        db.commit()
    return {"success": True, "users": len(users)}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def backup_account_home(self, username: str) -> dict:
    """
    Minimal backup job: tar.gz the user's home into /home/<user>/backups.
    (Runs on server; requires filesystem access.)
    """
    base = Path("/home") / username
    if not base.exists():
        raise RuntimeError("user home not found")

    backups = base / "backups"
    backups.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive = backups / f"home-{username}-{ts}.tar.gz"

    # Use tar via python (safe paths)
    import tarfile

    with tarfile.open(archive, "w:gz") as tf:
        tf.add(str(base / "public_html"), arcname="public_html", recursive=True)
        tf.add(str(base / "mail"), arcname="mail", recursive=True) if (base / "mail").exists() else None
        tf.add(str(base / "logs"), arcname="logs", recursive=True) if (base / "logs").exists() else None

    return {"success": True, "archive": str(archive)}

