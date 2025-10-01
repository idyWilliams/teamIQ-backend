from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from app.core.database import Base

class DashboardMetrics(Base):
    __tablename__ = "dashboard_metrics"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    active_projects = Column(Integer, default=0, nullable=False)
    overall_progress = Column(Integer, default=0, nullable=False)
    skills_tracked = Column(Integer, default=0, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    tasks_pending = Column(Integer, default=0, nullable=False)
    completion_rate = Column(Float, default=0.0, nullable=False)
    completion_rate_change = Column(Float, default=0.0, nullable=False)

    overall_score = Column(Float, default=0.0, nullable=False)

    skills_summary = Column(JSON, default={})
    contributions_timeseries = Column(JSON, default=[])

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OrgDashboardMetrics(Base):
    __tablename__ = "org_dashboard_metrics"

    org_id = Column(Integer, ForeignKey("organizations.id"), primary_key=True, index=True)

    team_members = Column(Integer, default=0, nullable=False)
    active_projects = Column(Integer, default=0, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    tasks_pending = Column(Integer, default=0, nullable=False)
    tasks_unassigned = Column(Integer, default=0, nullable=False)
    team_performance = Column(Float, default=0.0, nullable=False)
    task_completion_trend = Column(Float, default=0.0, nullable=False)

    project_summaries = Column(JSON, default={})

    team_member_summary = Column(JSON, default=[])
    active_blockers = Column(JSON, default=[])

    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
