from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, List

from app.models.dashboard import DashboardMetrics, OrgDashboardMetrics
from app.models.task import Task, TaskStatus
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.models.skill import UserSkill, Skill
from app.models.organization import UserRole, Organization


def compute_task_stats(db: Session, user_id: int):
    total = db.query(func.count(Task.id)).filter(Task.owner_id == user_id).scalar() or 0
    completed = db.query(func.count(Task.id)).filter(Task.owner_id == user_id, Task.status == TaskStatus.DONE).scalar() or 0
    pending = total - completed
    rate = (completed / total * 100) if total else 0.0

    since = datetime.utcnow() - timedelta(days=7)
    prev_since = since - timedelta(days=7)
    recent_completed = db.query(func.count(Task.id)).filter(Task.owner_id == user_id, Task.status == TaskStatus.DONE, Task.completed_at >= since).scalar() or 0
    prev_completed = db.query(func.count(Task.id)).filter(Task.owner_id == user_id, Task.status == TaskStatus.DONE, Task.completed_at >= prev_since, Task.completed_at < since).scalar() or 0
    change = ((recent_completed - prev_completed) / prev_completed * 100) if prev_completed else 0.0 if not recent_completed else 100.0
    return {"tasks_total": total, "tasks_completed": completed, "tasks_pending": pending, "completion_rate": rate, "completion_rate_change": change}


def compute_skill_summary(db: Session, user_id: int) -> Dict[str, float]:
    rows = (
        db.query(Skill.name, UserSkill.level)
        .join(UserSkill, Skill.id == UserSkill.skill_id)
        .filter(UserSkill.user_id == user_id)
        .all()
    )
    return {name: float(level) for name, level in rows}


def compute_timeseries(db: Session, user_id: int, days: int = 30) -> List[Dict]:
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date_trunc("day", Task.completed_at).label("day"), func.count(Task.id))
        .filter(Task.owner_id == user_id, Task.status == TaskStatus.DONE, Task.completed_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": row.day.date().isoformat(), "value": int(row[1])} for row in rows]


def compute_project_stats(db: Session, user_id: int):
    active = db.query(func.count(Project.id)).filter(Project.owner_id == user_id, Project.status == ProjectStatus.ACTIVE).scalar() or 0
    progress = db.query(func.avg(Project.pct_complete)).filter(Project.owner_id == user_id).scalar() or 0.0
    return {"active_projects": active, "overall_progress": int(progress)}


def compute_and_upsert_dashboard_metrics(db: Session, user_id: int):
    task_stats = compute_task_stats(db, user_id)
    skills = compute_skill_summary(db, user_id)
    series = compute_timeseries(db, user_id)
    project_stats = compute_project_stats(db, user_id)

    metrics = db.query(DashboardMetrics).filter(DashboardMetrics.user_id == user_id).first()
    if not metrics:
        metrics = DashboardMetrics(user_id=user_id)
        db.add(metrics)

    metrics.active_projects = project_stats["active_projects"]
    metrics.overall_progress = project_stats["overall_progress"]
    metrics.skills_tracked = len(skills)
    metrics.tasks_completed = task_stats["tasks_completed"]
    metrics.tasks_pending = task_stats["tasks_pending"]
    metrics.completion_rate = task_stats["completion_rate"]
    metrics.completion_rate_change = task_stats["completion_rate_change"]
    metrics.overall_score = (task_stats["completion_rate"] + project_stats["overall_progress"]) / 2
    metrics.skills_summary = list(skills.items())
    metrics.contributions_timeseries = series
    metrics.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(metrics)
    return metrics


def get_cached_dashboard(db: Session, user_id: int):
    return db.query(DashboardMetrics).filter(DashboardMetrics.user_id == user_id).first()


def compute_org_metrics(db: Session, org_id: int):
    """
    Compute organization dashboard metrics using many-to-many relationship
    """
    # ✅ FIXED: Query users who belong to this organization via many-to-many
    interns = (
        db.query(User)
        .join(User.organizations)  # Join through the many-to-many relationship
        .filter(
            Organization.id == org_id,
            User.role == UserRole.INTERN
        )
        .all()
    )

    if not interns:
        return None

    intern_summaries = []
    rates = []
    tasks_completed = 0
    tasks_pending = 0

    for intern in interns:
        metrics = get_cached_dashboard(db, intern.id) or compute_and_upsert_dashboard_metrics(db, intern.id)
        intern_summaries.append({
            "user_id": intern.id,
            "name": f"{intern.first_name} {intern.last_name}".strip(),
            "completion_rate": float(metrics.completion_rate or 0),
            "skills_tracked": metrics.skills_tracked
        })
        rates.append(float(metrics.completion_rate or 0))
        tasks_completed += metrics.tasks_completed
        tasks_pending += metrics.tasks_pending

    # ✅ FIXED: Active projects - query by organization_id directly
    active_projects = (
        db.query(func.count(Project.id))
        .filter(
            Project.organization_id == org_id,
            Project.status == ProjectStatus.ACTIVE
        )
        .scalar() or 0
    )

    team_members = len(interns)

    # Unassigned tasks: owner_id None, org_id set
    unassigned_tasks = (
        db.query(func.count(Task.id))
        .filter(
            Task.owner_id.is_(None),
            Task.organization_id == org_id
        )
        .scalar() or 0
    )

    team_performance = (sum(rates) / team_members) if team_members else 0.0
    task_completion_trend = 5.0  # Placeholder

    project_summaries = {"Project A": {"progress": 80}}  # Dummy
    team_member_summary = intern_summaries
    active_blockers = [{"id": 1, "description": "Resource shortage"}]  # Dummy

    org_metrics = db.query(OrgDashboardMetrics).filter(OrgDashboardMetrics.org_id == org_id).first()
    if not org_metrics:
        org_metrics = OrgDashboardMetrics(org_id=org_id)
        db.add(org_metrics)

    org_metrics.team_members = team_members
    org_metrics.active_projects = active_projects
    org_metrics.tasks_completed = tasks_completed
    org_metrics.tasks_pending = tasks_pending
    org_metrics.tasks_unassigned = unassigned_tasks
    org_metrics.team_performance = team_performance
    org_metrics.task_completion_trend = task_completion_trend
    org_metrics.project_summaries = project_summaries
    org_metrics.team_member_summary = team_member_summary
    org_metrics.active_blockers = active_blockers
    org_metrics.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(org_metrics)
    return org_metrics


def get_cached_org_dashboard(db: Session, org_id: int):
    return db.query(OrgDashboardMetrics).filter(OrgDashboardMetrics.org_id == org_id).first()
