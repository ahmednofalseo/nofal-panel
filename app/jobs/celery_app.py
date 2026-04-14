from __future__ import annotations

import os

from celery import Celery


def make_celery() -> Celery:
    broker = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    backend = os.getenv("CELERY_RESULT_BACKEND") or broker
    app = Celery("nofal_panel", broker=broker, backend=backend, include=["app.jobs.tasks"])

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone=os.getenv("TZ", "UTC"),
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = make_celery()

