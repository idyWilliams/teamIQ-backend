from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from app.models.task import Task, TaskStatus
from app.models.activity import Activity, CommitActivity, PullRequestActivity
from app.schemas.analytics import (
    EngineeringHealthData,
    VelocityMetrics,
    QualityMetrics,
    TeamHealth
)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_engineering_health(self, project_id: int) -> EngineeringHealthData:
        now = datetime.now(timezone.utc)
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)

        # 1. Velocity & Pipeline Metrics
        velocity = self._calculate_velocity(project_id, last_week, last_month)

        # 2. Quality Metrics
        quality = self._calculate_quality(project_id)

        # 3. Team Health
        team_health = self._calculate_team_health(project_id, last_month)

        return EngineeringHealthData(
            velocity=velocity,
            code_quality=quality,
            team_health=team_health,
            generated_at=now
        )

    def _calculate_velocity(self, project_id: int, last_week: datetime, last_month: datetime) -> VelocityMetrics:
        # sprint_velocity: tasks completed in last 7 days
        completed_tasks_count = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.DONE,
            Task.completed_at >= last_week
        ).count()

        # pr_cycle_time: avg(merged_at - created_at) in hours for last 30 days
        merged_prs = self.db.query(PullRequestActivity).filter(
            PullRequestActivity.project_id == project_id,
            PullRequestActivity.merged_at.isnot(None),
            PullRequestActivity.merged_at >= last_month
        ).all()

        if merged_prs:
            total_cycle_time = 0.0
            for pr in merged_prs:
                created = pr.created_at
                merged = pr.merged_at
                
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if merged.tzinfo is None:
                    merged = merged.replace(tzinfo=timezone.utc)
                    
                total_cycle_time += (merged - created).total_seconds() / 3600 
            
            avg_cycle_time = total_cycle_time / len(merged_prs)
        else:
            avg_cycle_time = 0.0

        # weekly_deploys: count merged PRs as proxy for deploys
        deploy_count = self.db.query(PullRequestActivity).filter(
            PullRequestActivity.project_id == project_id,
            PullRequestActivity.merged_at.isnot(None),
            PullRequestActivity.merged_at >= last_week
        ).count()

        # build_success_rate: mock
        build_success_rate = 94.2

        return VelocityMetrics(
            sprint_velocity=float(completed_tasks_count),
            pr_cycle_time_hours=round(avg_cycle_time, 2),
            weekly_deploys=deploy_count,
            build_success_rate=build_success_rate
        )

    def _calculate_quality(self, project_id: int) -> QualityMetrics:
        # Fetch/Mock test_coverage
        test_coverage = 78.5  # Mock value

        # technical_debt_hours: sum estimated_hours for tasks with 'refactor' or 'debt' in tags
        tech_debt_tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.status != TaskStatus.DONE
        ).all()

        total_debt_hours = 0
        debt_keywords = ['refactor', 'debt', 'cleanup', 'technical-debt']
        
        for task in tech_debt_tasks:
            if task.tags:
                tags = task.tags if isinstance(task.tags, list) else []
                if any(kw in [t.lower() for t in tags] for kw in debt_keywords):
                    total_debt_hours += (task.estimated_hours or 0)

        return QualityMetrics(
            test_coverage_percentage=test_coverage,
            technical_debt_hours=float(total_debt_hours)
        )

    def _calculate_team_health(self, project_id: int, last_month: datetime) -> TeamHealth:
        # burnout_risk: based on late-night and weekend activity
        activities = self.db.query(Activity).filter(
            Activity.project_id == project_id,
            Activity.timestamp >= last_month
        ).all()

        late_night_count = 0
        weekend_count = 0

        for act in activities:
            ts = act.timestamp
            # Ensure ts is timezone-aware if it's not
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            
            # Late night: 10 PM to 5 AM
            if ts.hour >= 22 or ts.hour <= 5:
                late_night_count += 1
            
            # Weekend: Saturday(5) or Sunday(6)
            if ts.weekday() >= 5:
                weekend_count += 1

        # Logic for risk level
        total_risk_indicators = late_night_count + weekend_count
        if total_risk_indicators > 50:
            risk = "high"
        elif total_risk_indicators > 15:
            risk = "medium"
        else:
            risk = "low"

        return TeamHealth(
            burnout_risk=risk,
            late_night_activity_count=late_night_count,
            weekend_activity_count=weekend_count
        )

def get_analytics_service(db: Session) -> AnalyticsService:
    return AnalyticsService(db)
