from typing import List
from pydantic import BaseModel
from datetime import datetime

class TaskStats(BaseModel):
    total: int
    completed: int
    pending: int
    completion_rate: float
    completion_rate_change: float  # New field for trends (e.g., +11.02%)

class ProjectStats(BaseModel):
    id: str
    name: str
    total_tasks: int
    done: int
    pct_complete: float

class SkillEntry(BaseModel):
    skill: str
    level: float

class TimeSeriesEntry(BaseModel):
    date: str
    commits: int

class ProjectSummaryEntry(BaseModel):
    name: str
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

class OrgSummaryEntry(BaseModel):
    user_id: str
    name: str
    completion_rate: float
    skills_tracked: int

class OrgDashboardResponse(BaseModel):
    org_id: str
    team_members: int
    active_projects: int
    tasks: TaskStats  # Includes completed, pending, unassigned
    team_performance: float
    task_completion_trend: float
    project_summaries: List[ProjectSummaryEntry] = []
    team_member_summary: List[TeamMemberSummaryEntry] = []
    active_blockers: List[ActiveBlockerEntry] = []
    last_updated: datetime