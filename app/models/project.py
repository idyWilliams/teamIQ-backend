# app/models/project.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Enum, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime
import enum


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class IntegrationMethod(str, enum.Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    # Step 1: Project Details
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    project_lead_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    stacks = Column(JSON, nullable=True)  # Array of tech stacks
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    linked_documents = Column(JSON, nullable=True)  # Array of document URLs
    project_image = Column(String, nullable=True)
    is_visible = Column(Boolean, default=True)

    # Step 2: Project Management Tool
    pm_tool = Column(String, nullable=True)  # jira, linear, clickup, etc.
    pm_integration_method = Column(Enum(IntegrationMethod), nullable=True)
    pm_project_id = Column(String, nullable=True)  # External project ID
    pm_api_key = Column(String, nullable=True)
    pm_access_token = Column(String, nullable=True)

    # Step 3: Version Control
    vc_tool = Column(String, nullable=True)  # github, gitlab, bitbucket
    vc_integration_method = Column(Enum(IntegrationMethod), nullable=True)
    vc_repository_url = Column(String, nullable=True)
    vc_api_key = Column(String, nullable=True)
    vc_access_token = Column(String, nullable=True)

    # Step 4: Communication Tool
    comm_tool = Column(String, nullable=True)  # slack, discord, teams
    comm_integration_method = Column(Enum(IntegrationMethod), nullable=True)
    comm_channel_id = Column(String, nullable=True)
    comm_api_key = Column(String, nullable=True)
    comm_webhook_url = Column(String, nullable=True)
    comm_notifications = Column(JSON, nullable=True)  # Notification preferences

    # Metadata
    owner_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    pct_complete = Column(Float, default=0.0)

    createdAt = Column(DateTime, default=datetime.datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    owner = relationship(
        "User",
        foreign_keys=[owner_id],            # disambiguate which FK links to User
        back_populates="owned_projects",
    )
    project_lead = relationship("User", foreign_keys=[project_lead_id])
    organization = relationship("Organization", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=True)  # developer, designer, etc.

    createdAt = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="members")
    user = relationship("User")
