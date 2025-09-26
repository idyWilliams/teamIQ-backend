from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.api.dashboard.models import DashboardMetrics, OrgDashboardMetrics

# --- ADJUST THESE IMPORTS to match your codebase: Task, Project, Skill, UserSkill ---
# Example placeholders (update to your actual module paths)
try:
    from app.api.tasks.models import Task
except Exception:
    Task = None

try:
    from app.api.projects.models import Project
except Exception:
    Project = None

try:
    from app.api.skills.models import Skill, UserSkill
except Exception:
    Skill = None
    UserSkill = None

try:
    from app.api.users.models import User
except Exception:
    User = None

def compute_task_stats(db: Session, user_id: str):
    """Count total/completed/pending tasks and compute completion rate with trend."""
    if Task is None:
        return {"tasks_total": 0, "tasks_completed": 0, "tasks_pending": 0, "completion_rate": 0.0, "completion_rate_change": 0.0}

    total = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id).scalar() or 0
    completed = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "done").scalar() or 0
    pending = total - completed
    rate = (completed / total * 100) if total else 0.0

    # Simple trend: compare last 7 days vs previous 7 days
    since = datetime.utcnow() - timedelta(days=7)
    prev_since = since - timedelta(days=7)
    recent_completed = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "done", Task.completed_at >= since).scalar() or 0
    prev_completed = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "done", Task.completed_at >= prev_since, Task.completed_at < since).scalar() or 0
    change = ((recent_completed - prev_completed) / prev_completed * 100) if prev_completed else 0.0 if not recent_completed else 100.0
    return {"tasks_total": total, "tasks_completed": completed, "tasks_pending": pending, "completion_rate": rate, "completion_rate_change": change}

def compute_skill_summary(db: Session, user_id: str):
    """Return dict {skill_name: level} for a user."""
    if Skill is None or UserSkill is None:
        return {}

    rows = (
        db.query(Skill.name, UserSkill.level)
        .join(UserSkill, Skill.id == UserSkill.skill_id)
        .filter(UserSkill.user_id == user_id)
        .all()
    )
    return {name: float(level) for name, level in rows}

def compute_timeseries(db: Session, user_id: str, days: int = 30):
    """Tasks completed per day (last `days`)."""
    if Task is None:
        return []

    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(func.date_trunc("day", Task.completed_at).label("day"), func.count(Task.id))
        .filter(Task.assignee_id == user_id, Task.status == "done", Task.completed_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": row.day.date().isoformat(), "commits": int(row[1])} for row in rows]

def compute_project_stats(db: Session, user_id: str):
    """Count active projects and overall progress (e.g., avg pct_complete)."""
    if Project is None:
        return {"active_projects": 0, "overall_progress": 0}

    active = db.query(func.count(Project.id)).filter(Project.assignee_id == user_id, Project.status == "active").scalar() or 0
    progress = db.query(func.avg(Project.pct_complete)).filter(Project.assignee_id == user_id).scalar() or 0.0
    return {"active_projects": active, "overall_progress": int(progress)}

def compute_and_upsert_dashboard_metrics(db: Session, user_id: str):
    """Compute per-user metrics and upsert into dashboard_metrics."""
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
    metrics.skills_tracked = len(skills) if skills else 0
    metrics.tasks_total = task_stats["tasks_total"]
    metrics.tasks_completed = task_stats["tasks_completed"]
    metrics.tasks_pending = task_stats["tasks_pending"]
    metrics.completion_rate = task_stats["completion_rate"]
    metrics.completion_rate_change = task_stats["completion_rate_change"]
    metrics.overall_score = (task_stats["completion_rate"] + project_stats["overall_progress"]) / 2 if task_stats["tasks_total"] else 0.0  # Simple average
    metrics.skills_summary = skills
    metrics.contributions_timeseries = series
    metrics.last_updated = datetime.utcnow()

    db.commit()
    db.refresh(metrics)
    return metrics

def get_cached_dashboard(db: Session, user_id: str):
    return db.query(DashboardMetrics).filter(DashboardMetrics.user_id == user_id).first()

# ---- Org-level computations ----
def compute_org_metrics(db: Session, org_id: str):
    """Aggregate intern dashboards for an organization and upsert into org_dashboard_metrics."""
    if User is None:
        return None

    interns = db.query(User).filter(User.organization_id == org_id, User.role == "intern").all()
    if not interns:
        return None

    intern_summaries = []
    rates = []
    skills_counts = []
    tasks_completed = 0
    tasks_pending = 0
    tasks_unassigned = 0
    for intern in interns:
        metrics = get_cached_dashboard(db, intern.id)
        if not metrics:
            metrics = compute_and_upsert_dashboard_metrics(db, intern.id)

        intern_summaries.append({
            "user_id": intern.id,
            "name": getattr(intern, "name", ""),
            "completion_rate": float(metrics.completion_rate or 0),
            "skills_tracked": metrics.skills_tracked
        })
        rates.append(float(metrics.completion_rate or 0))
        skills_counts.append(metrics.skills_tracked)
        tasks_completed += metrics.tasks_completed
        tasks_pending += metrics.tasks_pending

    # Aggregate project and team data (simplified; adjust based on Project/User models)
    active_projects = db.query(func.count(Project.id)).filter(Project.organization_id == org_id, Project.status == "active").scalar() or 0
    team_members = len(interns)
    unassigned_tasks = db.query(func.count(Task.id)).filter(Task.assignee_id.is_(None), Task.organization_id == org_id).scalar() or 0
    team_performance = (sum(rates) / team_members * 100) if team_members else 0.0
    task_completion_trend = ((tasks_completed / (tasks_completed + tasks_pending + unassigned_tasks) * 100) if (tasks_completed + tasks_pending + unassigned_tasks) else 0.0) - 50.0  # Example trend

    # Placeholder for project summaries and blockers (to be enhanced with real data)
    project_summaries = {
        "Mobile App v2.0": {"status": "In Progress", "next": "Beta", "release": "Jun 25"},
        "API Modernization": {"status": "Planning", "next": "Design", "release": "Jul 25"}
    }
    team_member_summary = [{"name": intern.name, "tasks": metrics.tasks_completed, "last_seen": "12:12"} for intern, metrics in [(i, get_cached_dashboard(db, i.id)) for i in interns] if metrics]
    active_blockers = [{"user": "Alex", "reason": "Blocked on API dependencies", "duration": "2hours"}]

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

def get_cached_org_dashboard(db: Session, org_id: str):
    return db.query(OrgDashboardMetrics).filter(OrgDashboardMetrics.org_id == org_id).first()