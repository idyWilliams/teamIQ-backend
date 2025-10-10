from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class TasksSummary(BaseModel):
    completed: int
    pending: int
    completion_rate: float
    completion_rate_change: float

class SkillSummary(BaseModel):
    skill: str
    level: float

class TimeseriesData(BaseModel):
    date: datetime
    value: float

class DashboardResponse(BaseModel):
    user_id: int
    active_projects: int
    overall_progress: int
    skills_tracked: int
    tasks: TasksSummary
    overall_score: float
    skills_summary: List[SkillSummary]
    contributions_timeseries: List[TimeseriesData]
    last_updated: datetime
    createdAt: datetime

class OrgTasksSummary(BaseModel):
    completed: int
    pending: int
    unassigned: int

class OrgDashboardResponse(BaseModel):
    org_id: str
    team_members: int
    active_projects: int
    tasks: OrgTasksSummary
    team_performance: float
    task_completion_trend: float
    project_summaries: Dict[str, Any]
    team_member_summary: List[Dict[str, Any]]
    active_blockers: List[Dict[str, Any]]
    last_updated: datetime
    createdAt: datetime
