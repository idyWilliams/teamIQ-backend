from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class VelocityMetrics(BaseModel):
    sprint_velocity: float
    pr_cycle_time_hours: float
    weekly_deploys: int
    build_success_rate: float

class QualityMetrics(BaseModel):
    test_coverage_percentage: float
    technical_debt_hours: float

class TeamHealth(BaseModel):
    burnout_risk: str # "low", "medium", "high"
    late_night_activity_count: int
    weekend_activity_count: int

class EngineeringHealthData(BaseModel):
    velocity: VelocityMetrics
    code_quality: QualityMetrics
    team_health: TeamHealth
    generated_at: datetime
