from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Boolean, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class TaskStatus(PyEnum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    # Basic fields
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.BACKLOG, index=True)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)

    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # External integration fields (KEY FOR BIDIRECTIONAL SYNC)
    external_id = Column(String, index=True, nullable=True)  # ID from Jira/ClickUp
    external_source = Column(String, index=True, nullable=True)  # "jira", "clickup", "linear"
    external_url = Column(String, nullable=True)  # Link to external task
    external_status = Column(String, nullable=True)  # Original status from external tool
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # Last sync time
    sync_enabled = Column(Boolean, default=True)  # Can disable sync for specific tasks

    # Additional metadata
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    tags = Column(JSON, nullable=True)  # ["frontend", "bug", "urgent"]
    attachments = Column(JSON, nullable=True)  # [{"url": "", "name": ""}]

    # Activity tracking
    view_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    # Timestamps
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="tasks")
    organization = relationship("Organization")
    project = relationship("Project", back_populates="tasks")
    comments = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")


class TaskComment(Base):
    """Track comments on tasks (from your app or synced from external tools)"""
    __tablename__ = "task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)

    # External sync
    external_id = Column(String, nullable=True)
    external_source = Column(String, nullable=True)

    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("Task", back_populates="comments")
    user = relationship("User")


class TaskHistory(Base):
    """Track all changes to tasks for activity timeline and AI analysis"""
    __tablename__ = "task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # What changed
    field_name = Column(String, nullable=False)  # "status", "assignee", "priority"
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)

    # Where the change came from
    source = Column(String, default="teamiq")  # "teamiq", "jira", "clickup"

    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task", back_populates="history")
    user = relationship("User")
