from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    domain_name = Column(String(255), unique=True, index=True, nullable=False)
    domain_type = Column(String(20), default="main")  # main / addon / subdomain / parked / redirect

    # Redirect (for parked/redirect domains)
    redirect_to = Column(String(255), nullable=True)
    redirect_type = Column(String(10), nullable=True)  # 301 / 302

    # Web Root
    document_root = Column(String(500), nullable=True)

    # DNS Settings
    ip_address = Column(String(45), nullable=True)
    nameserver1 = Column(String(100), nullable=True)
    nameserver2 = Column(String(100), nullable=True)

    # SSL
    has_ssl = Column(Boolean, default=False)
    ssl_expiry = Column(DateTime, nullable=True)
    force_https = Column(Boolean, default=False)

    # Nginx / Apache
    config_file = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="domains")
    dns_records = relationship("DNSRecord", back_populates="domain", cascade="all, delete-orphan")

class DNSRecord(Base):
    __tablename__ = "dns_records"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    record_type = Column(String(10), nullable=False)  # A, AAAA, MX, CNAME, TXT, SRV, NS, PTR
    name = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    ttl = Column(Integer, default=3600)
    priority = Column(Integer, default=0)  # For MX records
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="dns_records")
