"""
Contribution Model
Represents a single contribution from a version control system (e.g., a commit)
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user import User
from app.models.project import Project

class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    source = Column(String, nullable=False)  # e.g., "github", "gitlab"
    type = Column(String, nullable=False)  # e.g., "commit", "pull_request"
    external_id = Column(String, unique=True, index=True)
    message = Column(Text)
    timestamp = Column(DateTime, nullable=False)
    url = Column(String)

    user = relationship("User")
    project = relationship("Project")