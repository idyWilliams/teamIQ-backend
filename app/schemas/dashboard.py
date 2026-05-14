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
    user_name: Optional[str] = None
    display_name: Optional[str] = None
    job_title: Optional[str] = None
    avatar_url: Optional[str] = None
    online_status: str = "offline"

    # Core metrics
    metrics: Dict[str, Any]
    
    # Skill Analysis
    skill_analysis: Optional[Dict[str, Any]] = None

    # Activity data (for charts)
    activity_by_day: Dict[str, Any]
    top_languages: List[Dict[str, Any]]  
    top_projects: List[Dict[str, Any]]   

    # Insights
    ai_insights: Optional[Dict[str, Any]] = None

    # Timestamps
    last_activity_at: Optional[str] = None
    updated_at: str

    model_config = {"from_attributes": True}


# ==============================================================================
# ORGANIZATION DASHBOARD
# ==============================================================================

class OrgDashboardResponse(BaseModel):
    """Complete organization dashboard response"""
    organization_id: int
    org_id: int
    organization_name: str
    org_name: str
    org_logo: Optional[str] = None
    industry: Optional[str] = None
    subscription_plan: str = "Enterprise"

    # Aggregated metrics
    metrics: Dict[str, Any]
    
    # Tracks (Departments)
    tracks: List[Dict[str, Any]] = []
    
    # Skill Analysis
    skill_analysis: Optional[Dict[str, Any]] = None

    # Top performers
    top_contributors: List[Dict[str, Any]] = []

    # Timestamps
    updated_at: str

    model_config = {"from_attributes": True}
