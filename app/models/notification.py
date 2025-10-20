<<<<<<< HEAD
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from enum import Enum as PyEnum
from datetime import datetime
from app.models.organization import UserRole

class NotificationType(PyEnum):
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    PROJECT_COMPLETED = "project_completed"
    DAILY_SUMMARY = "daily_summary"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(SQLEnum(NotificationType, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    user = relationship("User", back_populates="notifications")

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_assigned_email = Column(Boolean, default=True)
    task_updated_email = Column(Boolean, default=True)
    project_completed_email = Column(Boolean, default=True)
    daily_summary_email = Column(Boolean, default=True)
    task_assigned_slack = Column(Boolean, default=False)
    task_updated_slack = Column(Boolean, default=False)
    project_completed_slack = Column(Boolean, default=False)
    user = relationship("User", back_populates="notification_preferences")
=======
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    type = Column(String, default="info")  # info, warning, success
    createdAt = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    organization = relationship("Organization")
>>>>>>> origin/staging
