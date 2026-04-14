from __future__ import annotations

from celery.schedules import crontab

from app.jobs.celery_app import celery_app


celery_app.conf.beat_schedule = {
    "collect-disk-usage-hourly": {
        "task": "app.jobs.tasks.collect_disk_usage",
        "schedule": crontab(minute=0, hour="*/1"),
    },
}

