from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.port_registry import PortRegistry


class PortAllocatorService:
    @staticmethod
    def allocate_for_user(db: Session, user_id: int, purpose: str = "instance") -> PortRegistry:
        """
        Allocate a free port in a transaction-safe way.
        SQLite won't lock like Postgres, but uniqueness constraint still prevents collisions.
        """
        # Fast path: reuse existing active port for this user/purpose.
        existing = (
            db.query(PortRegistry)
            .filter(and_(PortRegistry.user_id == user_id, PortRegistry.purpose == purpose, PortRegistry.is_active == True))
            .first()
        )
        if existing:
            return existing

        for port in range(settings.PORT_RANGE_START, settings.PORT_RANGE_END + 1):
            taken = db.query(PortRegistry).filter(and_(PortRegistry.port == port, PortRegistry.is_active == True)).first()
            if taken:
                continue
            row = PortRegistry(port=port, user_id=user_id, purpose=purpose, is_active=True)
            db.add(row)
            try:
                db.flush()
                return row
            except Exception:
                db.rollback()
                continue

        raise RuntimeError("No free ports available in range")

    @staticmethod
    def release_user_ports(db: Session, user_id: int) -> int:
        rows = db.query(PortRegistry).filter(and_(PortRegistry.user_id == user_id, PortRegistry.is_active == True)).all()
        for r in rows:
            r.is_active = False
            r.released_at = datetime.utcnow()
        db.flush()
        return len(rows)

