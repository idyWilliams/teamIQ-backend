from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func
from enum import Enum as PyEnum

class ProjectStatus(PyEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    pct_complete = Column(Float, default=0.0)

    owner = relationship("User", back_populates="projects")
    organization = relationship("Organization")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())