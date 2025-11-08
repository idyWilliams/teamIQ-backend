"""
Dashboard Metrics Models
Stores aggregated metrics for quick dashboard loading
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy.sql import func


class UserDashboard(Base):
    """
    Cached dashboard metrics for individual users
    Updated by background jobs and webhooks
    """
    __tablename__ = "user_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Task metrics (from Jira/ClickUp)
    tasks_total = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    tasks_in_progress = Column(Integer, default=0)
    tasks_overdue = Column(Integer, default=0)
    avg_completion_time_hours = Column(Float, default=0.0)

    # Code metrics (from GitHub/GitLab)
    commits_count = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    pull_requests_count = Column(Integer, default=0)
    pull_requests_merged = Column(Integer, default=0)
    code_reviews_given = Column(Integer, default=0)

    # Communication metrics (from Slack/Discord)
    messages_sent = Column(Integer, default=0)
    reactions_given = Column(Integer, default=0)
    files_shared = Column(Integer, default=0)

    # Productivity scores (AI/ML ready)
    productivity_score = Column(Float, default=0.0)  # 0-100
    collaboration_score = Column(Float, default=0.0)  # 0-100
    code_quality_score = Column(Float, default=0.0)  # 0-100
    consistency_score = Column(Float, default=0.0)  # 0-100

    # Time tracking
    total_active_days = Column(Integer, default=0)
    avg_daily_commits = Column(Float, default=0.0)
    avg_daily_tasks = Column(Float, default=0.0)

    # Streaks
    current_commit_streak = Column(Integer, default=0)
    longest_commit_streak = Column(Integer, default=0)
    current_task_streak = Column(Integer, default=0)

    # Activity breakdown (JSON for flexibility)
    activity_by_day = Column(JSON, default={})  # {"2025-11-07": {"commits": 5, "tasks": 3}}
    top_languages = Column(JSON, default=[])  # [{"name": "Python", "percentage": 45}]
    top_projects = Column(JSON, default=[])  # [{"name": "Project X", "contribution": 30}]

    # Timestamps
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")


class OrganizationDashboard(Base):
    """
    Cached dashboard metrics for organizations
    Aggregates all team member metrics
    """
    __tablename__ = "organization_dashboards"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), unique=True, nullable=False, index=True)

    # Team metrics
    total_members = Column(Integer, default=0)
    active_members = Column(Integer, default=0)  # Active in last 7 days

    # Project metrics
    total_projects = Column(Integer, default=0)
    active_projects = Column(Integer, default=0)
    completed_projects = Column(Integer, default=0)

    # Aggregate task metrics
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    in_progress_tasks = Column(Integer, default=0)
    avg_task_completion_rate = Column(Float, default=0.0)  # Percentage

    # Aggregate code metrics
    total_commits = Column(Integer, default=0)
    total_pull_requests = Column(Integer, default=0)
    total_lines_changed = Column(Integer, default=0)

    # Communication metrics
    total_messages = Column(Integer, default=0)
    avg_response_time_minutes = Column(Float, default=0.0)

    # Team performance scores
    overall_productivity = Column(Float, default=0.0)  # 0-100
    team_collaboration = Column(Float, default=0.0)  # 0-100
    code_quality = Column(Float, default=0.0)  # 0-100

    # Top performers (JSON)
    top_contributors = Column(JSON, default=[])  # [{"user_id": 15, "score": 95}]
    most_active_projects = Column(JSON, default=[])
    technology_breakdown = Column(JSON, default={})

    # Time-based metrics
    activity_trend = Column(JSON, default={})  # Last 30 days
    velocity_trend = Column(JSON, default={})  # Sprint velocity

    # Timestamps
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")


# ✅ ALIASES (NOT indented - at module level)
DashboardMetrics = UserDashboard
OrgDashboardMetrics = OrganizationDashboard
