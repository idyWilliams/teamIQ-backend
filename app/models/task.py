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
    status = Column(Enum(TaskStatus, values_callable=lambda obj: [e.value for e in obj]), default=TaskStatus.BACKLOG, index=True)
    priority = Column(Enum(TaskPriority, values_callable=lambda obj: [e.value for e in obj]), default=TaskPriority.MEDIUM)

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

    # Blocker info
    is_blocked = Column(Boolean, default=False)
    blocker_details = Column(Text, nullable=True)

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

    @property
    def display_task_id(self):
        return f"#TSK-{self.id}"

    @property
    def status_color(self):
        colors = {
            TaskStatus.BACKLOG: "#6c757d",
            TaskStatus.TODO: "#007bff",
            TaskStatus.IN_PROGRESS: "#ffc107",
            TaskStatus.DONE: "#28a745"
        }
        return colors.get(self.status, "#6c757d")

    @property
    def category_color(self):
        colors = {
            TaskPriority.LOW: "#28a745",
            TaskPriority.MEDIUM: "#17a2b8",
            TaskPriority.HIGH: "#fd7e14",
            TaskPriority.URGENT: "#dc3545"
        }
        return colors.get(self.priority, "#17a2b8")

    @property
    def assignees(self):
        if self.owner:
            return [{
                "id": self.owner.id,
                "name": self.owner.display_name,
                "avatar_url": self.owner.avatar_url
            }]
        return []

    @property
    def attachment_count(self):
        return len(self.attachments) if self.attachments else 0

    @property
    def message_count(self):
        return self.comment_count

    @property
    def file_count(self):
        return self.attachment_count


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
