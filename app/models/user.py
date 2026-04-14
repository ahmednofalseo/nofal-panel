from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # admin / reseller / user
    is_active = Column(Boolean, default=True)
    is_suspended = Column(Boolean, default=False)
    suspend_reason = Column(String(255), nullable=True)

    # Package
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)
    package = relationship("Package", back_populates="users")

    # Resource Limits (from package)
    disk_quota_mb = Column(Integer, default=1024)      # MB
    bandwidth_limit_mb = Column(BigInteger, default=10240)  # MB/month
    email_limit = Column(Integer, default=10)
    db_limit = Column(Integer, default=5)
    ftp_limit = Column(Integer, default=5)
    subdomain_limit = Column(Integer, default=10)
    addon_domain_limit = Column(Integer, default=2)
    parked_domain_limit = Column(Integer, default=5)

    # Resource Usage (updated periodically)
    disk_used_mb = Column(Integer, default=0)
    bandwidth_used_mb = Column(BigInteger, default=0)

    # Contact Info
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
    company = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)

    # Server Info
    primary_domain = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    nameserver1 = Column(String(100), nullable=True)
    nameserver2 = Column(String(100), nullable=True)
    server_user = Column(String(50), nullable=True)  # Linux system user

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    domains = relationship("Domain", back_populates="user", cascade="all, delete-orphan")
    email_accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")
    db_accounts = relationship("DatabaseAccount", back_populates="user", cascade="all, delete-orphan")
    ftp_accounts = relationship("FtpAccount", back_populates="user", cascade="all, delete-orphan")
    cron_jobs = relationship("CronJob", back_populates="user", cascade="all, delete-orphan")
    ssl_certs = relationship("SSLCert", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )
