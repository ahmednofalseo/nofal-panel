from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)   # part before @
    domain = Column(String(255), nullable=False)     # part after @
    hashed_password = Column(String(255), nullable=False)

    quota_mb = Column(Integer, default=1024)         # MB (0 = unlimited)
    used_mb = Column(Integer, default=0)

    # Forwarder
    is_forwarder = Column(Boolean, default=False)
    forward_to = Column(String(500), nullable=True)

    # Autoresponder
    has_autoresponder = Column(Boolean, default=False)
    autoresponder_subject = Column(String(255), nullable=True)
    autoresponder_body = Column(String(2000), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="email_accounts")
