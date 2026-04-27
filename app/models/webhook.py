"""
Webhook Status Tracking
Monitors webhook health and delivery
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class WebhookStatus(Base):
    """
    Tracks webhook configuration and health per project
    Ensures webhooks persist across sessions
    """
    __tablename__ = "webhook_statuses"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # Webhook details
    tool_type = Column(String, nullable=False)  # "pm_tool", "vc_tool", "comm_tool"
    tool_name = Column(String, nullable=False)  # "jira", "github", "slack"
    webhook_url = Column(String, nullable=False)

    # Configuration status
    is_configured = Column(Boolean, default=False)  # User completed setup
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Health monitoring
    total_events_received = Column(Integer, default=0)
    last_event_received_at = Column(DateTime(timezone=True), nullable=True)
    last_event_type = Column(String, nullable=True)

    # Error tracking
    failed_deliveries = Column(Integer, default=0)
    last_error = Column(String, nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    configuration_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project")
