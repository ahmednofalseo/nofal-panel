from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class DatabaseAccount(Base):
    __tablename__ = "db_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    db_name = Column(String(100), unique=True, index=True, nullable=False)
    db_user = Column(String(100), nullable=False)
    db_password_hint = Column(String(100), nullable=True)  # Store only hint for display
    db_host = Column(String(100), default="localhost")
    db_port = Column(Integer, default=3306)

    # Privileges
    privileges = Column(Text, default="ALL PRIVILEGES")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="db_accounts")
