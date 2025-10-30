# app/models/integration.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime
import enum


class AuthMethod(str, enum.Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    API_TOKEN = "api_token"
    BOT_TOKEN = "bot_token"
    PERSONAL_ACCESS_TOKEN = "personal_access_token"


class IntegrationType(str, enum.Enum):
    # Project Management
    JIRA = "jira"
    LINEAR = "linear"
    CLICKUP = "clickup"
    ASANA = "asana"

    # Version Control
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"

    # Communication
    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"


class OrganizationIntegration(Base):
    """
    Store organization-wide integration credentials.
    This is set up ONCE per organization, then reused for all projects.
    """
    __tablename__ = "organization_integrations"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # Integration details
    integration_type = Column(String, nullable=False)  # jira, github, slack, etc.
    integration_name = Column(String, nullable=True)  # Display name

    # Authentication
    auth_method = Column(Enum(AuthMethod), nullable=False)

    # OAuth 2.0 tokens
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # API Keys/Tokens
    api_key = Column(Text, nullable=True)
    api_token = Column(Text, nullable=True)

    # Tool-specific config
    base_url = Column(String, nullable=True)  # For self-hosted instances
    workspace_id = Column(String, nullable=True)
    workspace_name = Column(String, nullable=True)
    team_id = Column(String, nullable=True)

    # Additional metadata
    config = Column(JSON, nullable=True)  # Tool-specific configuration
    scopes = Column(JSON, nullable=True)  # OAuth scopes

    # Status
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime, nullable=True)

    # Setup tracking
    setup_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    createdAt = Column(DateTime, default=datetime.datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="integrations")
    setup_by = relationship("User")


from sqlalchemy.sql import func

class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    provider = Column(String, nullable=False) # e.g., "github", "slack"
    provider_id = Column(String, nullable=False, unique=True) # e.g., github user login
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
