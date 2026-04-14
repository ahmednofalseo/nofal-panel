from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PortRegistry(Base):
    __tablename__ = "port_registry"

    id = Column(Integer, primary_key=True, index=True)
    port = Column(Integer, unique=True, index=True, nullable=False)

    # who owns it
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # what is it for
    purpose = Column(String(30), default="instance")  # instance / reserved / system
    is_active = Column(Boolean, default=True)

    reserved_at = Column(DateTime(timezone=True), server_default=func.now())
    released_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")

