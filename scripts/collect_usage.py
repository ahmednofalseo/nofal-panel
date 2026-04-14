from __future__ import annotations

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User
from app.services.analytics import AnalyticsService


def main() -> int:
    db: Session = SessionLocal()
    try:
        users = db.query(User).filter(User.role != "admin").all()
        for u in users:
            u.disk_used_mb = AnalyticsService.disk_usage_mb(u.username)
        db.commit()
        print(f"updated {len(users)} users")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

