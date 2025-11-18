from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, index=True)
    provider = Column(String, index=True)
    account_id = Column(String, index=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    connected_by_user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class OrganizationIntegration(Base):
    """Model for organization integrations - REQUIRED by Organization model"""
    __tablename__ = "organization_integrations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    integration_type = Column(String, nullable=False)
    integration_name = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to Organization
    organization = relationship("Organization", back_populates="integrations")


class LinkedAccount(Base):
    """Model for linked third-party accounts"""
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    provider = Column(String, nullable=False)
    provider_user_id = Column(String, nullable=False)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
