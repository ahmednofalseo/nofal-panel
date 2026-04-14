from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class CronJob(Base):
    __tablename__ = "cron_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=True)
    command = Column(Text, nullable=False)
    minute = Column(String(20), default="*")
    hour = Column(String(20), default="*")
    day_of_month = Column(String(20), default="*")
    month = Column(String(20), default="*")
    day_of_week = Column(String(20), default="*")

    email_output = Column(String(255), nullable=True)  # Send output to email
    is_active = Column(Boolean, default=True)

    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="cron_jobs")

    @property
    def cron_expression(self):
        return f"{self.minute} {self.hour} {self.day_of_month} {self.month} {self.day_of_week}"
