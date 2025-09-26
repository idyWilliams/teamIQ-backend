from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base

class DashboardMetrics(Base):
    __tablename__ = "dashboard_metrics"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True, index=True)
    active_projects = Column(Integer, default=0, nullable=False)  # E.g., 22 from designs
    overall_progress = Column(Integer, default=0, nullable=False)  # E.g., 22
    skills_tracked = Column(Integer, default=0, nullable=False)  # E.g., 3
    tasks_completed = Column(Integer, default=0, nullable=False)  # E.g., 22
    tasks_pending = Column(Integer, default=0, nullable=False)  # E.g., 3
    completion_rate = Column(Float, default=0.0, nullable=False)  # E.g., 38.0 (percentage)
    completion_rate_change = Column(Float, default=0.0, nullable=False)  # E.g., +11.02 for trends

    overall_score = Column(Float, default=0.0, nullable=False)  # E.g., 70.0 out of 100

    skills_summary = Column(JSONB, default={})  # E.g., {"React": 80.0, "Typescript": 80.0, "Communicate": 80.0, "Python": 80.0, "Design": 80.0, "Micro Services": 80.0}; use percentages
    contributions_timeseries = Column(JSONB, default=[])  # E.g., [{"date": "2025-09-25", "commits": 2},] 

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())



class OrgDashboardMetrics(Base):
    __tablename__ = "org_dashboard_metrics"

    org_id = Column(String, ForeignKey("organizations.id"), primary_key=True, index=True)
    
    # Overview Section
    team_members = Column(Integer, default=0, nullable=False)  # E.g., 22 from design
    active_projects = Column(Integer, default=0, nullable=False)  # E.g., 22
    tasks_completed = Column(Integer, default=0, nullable=False)  # E.g., 22
    tasks_pending = Column(Integer, default=0, nullable=False)  # E.g., 3
    tasks_unassigned = Column(Integer, default=0, nullable=False)  # E.g., 3
    team_performance = Column(Float, default=0.0, nullable=False)  # E.g., 100.0 (percentage)
    task_completion_trend = Column(Float, default=0.0, nullable=False)  # E.g., 65.0 (percentage trend)

    # Project Status Section
    project_summaries = Column(JSONB, default={})  # E.g., {"Mobile App v2.0": {"status": "In Progress", "next": "Beta", "release": "Jun 25"}, ...}

    # Team Section
    team_member_summary = Column(JSONB, default=[])  # E.g., [{"name": "Jacob Jones", "tasks": 12, "last_seen": "12:12"}, ...]
    active_blockers = Column(JSONB, default=[])  # E.g., [{"user": "Alex", "reason": "Blocked on API dependencies", "duration": "2hours"}, ...]

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
