"""
Dashboard Response Schemas
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any  # ✅ Added Any
from datetime import datetime


# ==============================================================================
# USER DASHBOARD
# ==============================================================================

class TaskMetrics(BaseModel):
    """Task-related metrics"""
    total: int
    completed: int
    in_progress: int
    overdue: int
    completion_rate: float  # Percentage
    avg_completion_time_hours: float


class CodeMetrics(BaseModel):
    """Code contribution metrics"""
    commits_count: int
    lines_added: int
    lines_deleted: int
    net_lines: int
    pull_requests_total: int
    pull_requests_merged: int
    merge_rate: float  # Percentage
    code_reviews_given: int


class CommunicationMetrics(BaseModel):
    """Communication activity metrics"""
    messages_sent: int
    reactions_given: int
    files_shared: int
    avg_daily_messages: float


class ProductivityScores(BaseModel):
    """AI-calculated productivity scores"""
    overall: float  # 0-100
    collaboration: float
    code_quality: float
    consistency: float

    # Breakdown explanation
    factors: Dict[str, float] = {
        "task_completion": 0.0,
        "code_contribution": 0.0,
        "team_collaboration": 0.0,
        "consistency": 0.0
    }


class ActivityBreakdown(BaseModel):
    """Daily activity breakdown"""
    date: str
    commits: int
    tasks_completed: int
    messages: int
    total_score: float


class DashboardResponse(BaseModel):
    """Complete user dashboard response"""
    user_id: int

    # Core metrics
    tasks: TaskMetrics
    code: CodeMetrics
    communication: CommunicationMetrics
    scores: ProductivityScores

    # Streaks
    current_commit_streak: int
    longest_commit_streak: int
    current_task_streak: int

    # Time tracking
    total_active_days: int
    last_activity_at: Optional[datetime]

    # Activity data (for charts)
    activity_by_day: List[ActivityBreakdown]
    top_languages: List[Dict[str, Any]]  
    top_projects: List[Dict[str, Any]]   

    # Timestamps
    updated_at: datetime

    model_config = {"from_attributes": True}  # ✅ Pydantic v2 style


# ==============================================================================
# ORGANIZATION DASHBOARD
# ==============================================================================

class TeamMetrics(BaseModel):
    """Team composition metrics"""
    total_members: int
    active_members: int
    activity_rate: float  # Percentage


class ProjectMetrics(BaseModel):
    """Project progress metrics"""
    total: int
    active: int
    completed: int
    completion_rate: float


class TeamPerformance(BaseModel):
    """Team-wide performance scores"""
    overall_productivity: float
    team_collaboration: float
    code_quality: float
    velocity: float  # Tasks completed per week


class TopContributor(BaseModel):
    """Top performer data"""
    user_id: int
    name: str
    score: float
    avatar: Optional[str]
    contributions: Dict[str, int]


class OrgDashboardResponse(BaseModel):
    """Complete organization dashboard response"""
    organization_id: int

    # Team metrics
    team: TeamMetrics
    projects: ProjectMetrics

    # Aggregate metrics
    total_tasks: int
    completed_tasks: int
    total_commits: int
    total_pull_requests: int
    total_messages: int

    # Performance
    performance: TeamPerformance

    # Top performers
    top_contributors: List[TopContributor]
    most_active_projects: List[Dict[str, Any]]
    technology_breakdown: Dict[str, float]

    # Trends (for charts)
    activity_trend: Dict[str, int]  # Last 30 days
    velocity_trend: Dict[str, float]  # Last 10 sprints

    # Timestamps
    updated_at: datetime

    model_config = {"from_attributes": True}
