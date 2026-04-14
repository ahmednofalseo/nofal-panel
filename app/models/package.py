from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from app.database import Base

class Package(Base):
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    # Disk & Bandwidth
    disk_quota_mb = Column(Integer, default=1024)        # MB (0 = unlimited)
    bandwidth_limit_mb = Column(BigInteger, default=10240)  # MB/month (0 = unlimited)

    # Account Limits
    email_limit = Column(Integer, default=10)          # 0 = unlimited
    db_limit = Column(Integer, default=5)              # MySQL databases
    ftp_limit = Column(Integer, default=5)             # FTP accounts
    subdomain_limit = Column(Integer, default=10)      # Subdomains
    addon_domain_limit = Column(Integer, default=2)    # Addon domains
    parked_domain_limit = Column(Integer, default=5)   # Parked domains

    # Features
    has_ssh = Column(Boolean, default=False)
    has_cron = Column(Boolean, default=True)
    has_ssl = Column(Boolean, default=True)
    has_softaculous = Column(Boolean, default=False)
    has_backup = Column(Boolean, default=True)
    max_processes = Column(Integer, default=25)
    max_connections = Column(Integer, default=25)

    # PHP Settings
    php_version = Column(String(10), default="8.1")
    max_upload_size_mb = Column(Integer, default=128)
    max_execution_time = Column(Integer, default=300)
    memory_limit_mb = Column(Integer, default=256)

    # Pricing
    price_monthly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="package")
