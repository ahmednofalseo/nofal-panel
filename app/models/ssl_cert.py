from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class SSLCert(Base):
    __tablename__ = "ssl_certs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    domain = Column(String(255), nullable=False)
    cert_type = Column(String(20), default="letsencrypt")  # letsencrypt / self-signed / custom
    cert_path = Column(String(500), nullable=True)
    key_path = Column(String(500), nullable=True)
    chain_path = Column(String(500), nullable=True)

    issued_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="ssl_certs")
