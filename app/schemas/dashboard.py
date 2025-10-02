from typing import List, Dict
from pydantic import BaseModel
from datetime import datetime

class TaskStats(BaseModel):
    completed: int
    pending: int
    unassigned: int = 0
    completion_rate: float = 0.0
    completion_rate_change: float = 0.0

class SkillEntry(BaseModel):
    skill: str
    level: float

class TimeSeriesEntry(BaseModel):
    date: str
    commits: int

class ProjectSummary(BaseModel):
    status: str
    next: str
    release: str

class TeamMemberSummaryEntry(BaseModel):
    name: str
    tasks: int
    last_seen: str

class ActiveBlockerEntry(BaseModel):
    user: str
    reason: str
    duration: str

class DashboardResponse(BaseModel):
    user_id: str
    active_projects: int
    overall_progress: int
    skills_tracked: int
    tasks: TaskStats
    overall_score: float
    skills_summary: List[SkillEntry] = []
    contributions_timeseries: List[TimeSeriesEntry] = []
    last_updated: datetime

class OrgDashboardResponse(BaseModel):
    org_id: str
    team_members: int
    active_projects: int
    tasks: TaskStats
    team_performance: float
    task_completion_trend: float
    project_summaries: Dict[str, ProjectSummary] = {}
    team_member_summary: List[TeamMemberSummaryEntry] = []
    active_blockers: List[ActiveBlockerEntry] = []
    last_updated: datetime
