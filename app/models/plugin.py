from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Plugin(Base):
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, index=True, nullable=False)
    version = Column(String(40), default="0.0.0")
    enabled = Column(Boolean, default=False, nullable=False)
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

