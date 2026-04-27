from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func
from enum import Enum as PyEnum


class ActivityType(PyEnum):
    # Communication activities
    MESSAGE = "message"
    REACTION = "reaction"
    MENTION = "mention"
    THREAD_REPLY = "thread_reply"

    # Code activities
    COMMIT = "commit"
    PULL_REQUEST = "pull_request"
    CODE_REVIEW = "code_review"
    PR_COMMENT = "pr_comment"
    PR_MERGE = "pr_merge"

    # Task activities
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_COMMENT = "task_comment"
    TASK_ASSIGNED = "task_assigned"

    # Collaboration
    FILE_UPLOAD = "file_upload"
    MEETING_ATTENDED = "meeting_attended"


class Activity(Base):
    """Comprehensive activity tracking for AI/ML analysis"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)

    # Who did it
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # What happened
    type = Column(String, nullable=False, index=True)  # ActivityType
    source = Column(String, nullable=False, index=True)  # "slack", "github", "jira", "teamiq"
    action = Column(String, nullable=False)  # "created", "updated", "deleted", "sent"

    # Details
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    activity_metadata = Column(JSON, nullable=True)  # ✅ FIXED: renamed from 'metadata' to 'activity_metadata'

    # External reference
    external_id = Column(String, index=True, nullable=True)
    external_url = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)  # For Slack/Discord

    # Metrics (for productivity scoring)
    impact_score = Column(Float, default=0.0)  # 0-10 scale
    complexity_score = Column(Float, default=0.0)  # For commits/PRs

    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    project = relationship("Project")


class CommitActivity(Base):
    """Detailed commit tracking from GitHub/GitLab/Bitbucket"""
    __tablename__ = "commit_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Commit details
    commit_sha = Column(String, unique=True, index=True)
    message = Column(Text, nullable=False)
    branch = Column(String, nullable=True)
    repository = Column(String, nullable=False)

    # Code metrics
    files_changed = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    files = Column(JSON, nullable=True)  # List of files changed

    # External
    external_url = Column(String, nullable=True)
    source = Column(String, nullable=False)  # "github", "gitlab", "bitbucket"

    timestamp = Column(DateTime(timezone=True), nullable=False)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    project = relationship("Project")


class PullRequestActivity(Base):
    """Track PRs and code reviews"""
    __tablename__ = "pull_request_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # PR details
    pr_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    state = Column(String, nullable=False)  # "open", "merged", "closed"

    # Metrics
    files_changed = Column(Integer, default=0)
    commits_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    reviews_count = Column(Integer, default=0)

    # External
    external_id = Column(String, index=True)
    external_url = Column(String, nullable=True)
    source = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False)
    merged_at = Column(DateTime(timezone=True), nullable=True)
    synced_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    project = relationship("Project")
