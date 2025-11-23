from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class ProjectResource(Base):
    __tablename__ = "project_resources"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    connection_id = Column(Integer, ForeignKey("integration_connections.id"), nullable=False)

    resource_id = Column(String, nullable=False)  # ID from external provider (e.g. repo ID, channel ID)
    resource_type = Column(String, nullable=False) # repository, channel, project, etc.
    resource_name = Column(String, nullable=False)
    resource_metadata = Column(JSON, nullable=True)  # Renamed from metadata to avoid conflict # Store extra info like URL, description

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="resources")
    connection = relationship("IntegrationConnection")
