"""Per-user key/value preferences for cPanel-style tools (JSON or plain text)."""
import json
from typing import Any, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Session, relationship

from app.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (UniqueConstraint("user_id", "pref_key", name="uq_user_pref_key"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pref_key = Column(String(80), nullable=False)
    pref_value = Column(Text, nullable=True)

    user = relationship("User", back_populates="preferences")


def pref_get_json(db: Session, user_id: int, key: str, default: Any) -> Any:
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.pref_key == key)
        .first()
    )
    if not row or row.pref_value is None:
        return default
    try:
        return json.loads(row.pref_value)
    except json.JSONDecodeError:
        return default


def pref_set_json(db: Session, user_id: int, key: str, value: Any) -> None:
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.pref_key == key)
        .first()
    )
    serialized = json.dumps(value, ensure_ascii=False)
    if row:
        row.pref_value = serialized
    else:
        db.add(UserPreference(user_id=user_id, pref_key=key, pref_value=serialized))


def pref_get_text(db: Session, user_id: int, key: str, default: str = "") -> str:
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.pref_key == key)
        .first()
    )
    if not row or row.pref_value is None:
        return default
    return row.pref_value


def pref_set_text(db: Session, user_id: int, key: str, value: str) -> None:
    row = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == user_id, UserPreference.pref_key == key)
        .first()
    )
    if row:
        row.pref_value = value
    else:
        db.add(UserPreference(user_id=user_id, pref_key=key, pref_value=value))
