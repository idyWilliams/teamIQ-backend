from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.dashboard import services, schemas
from app.api.users.dependencies.auth import get_current_user  # Updated import

# Basic require_role implementation
def require_role(role: str):
    def role_checker(current_user=Depends(get_current_user)):
        if not hasattr(current_user, 'role') or current_user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/home", response_model=schemas.DashboardResponse)
def get_home_dashboard(background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    metrics = services.get_cached_dashboard(db, current_user.id)
    if not metrics:
        metrics = services.compute_and_upsert_dashboard_metrics(db, current_user.id)
    else:
        background_tasks.add_task(services.compute_and_upsert_dashboard_metrics, db, current_user.id)
    
    return {
        "user_id": current_user.id,
        "active_projects": metrics.active_projects,
        "overall_progress": metrics.overall_progress,
        "skills_tracked": metrics.skills_tracked,
        "tasks": {
            "completed": metrics.tasks_completed,
            "pending": metrics.tasks_pending,
            "completion_rate": metrics.completion_rate,
            "completion_rate_change": metrics.completion_rate_change,
        },
        "overall_score": metrics.overall_score,
        "skills_summary": [{"skill": k, "level": v} for k, v in (metrics.skills_summary or {}).items()],
        "contributions_timeseries": metrics.contributions_timeseries or [],
        "last_updated": metrics.last_updated,
    }

@router.get("/mentor/{intern_id}", response_model=schemas.DashboardResponse, dependencies=[Depends(require_role("mentor"))])
def get_intern_dashboard(intern_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    metrics = services.get_cached_dashboard(db, intern_id)
    if not metrics:
        metrics = services.compute_and_upsert_dashboard_metrics(db, intern_id)
    return {
        "user_id": intern_id,
        "active_projects": metrics.active_projects,
        "overall_progress": metrics.overall_progress,
        "skills_tracked": metrics.skills_tracked,
        "tasks": {
            "completed": metrics.tasks_completed,
            "pending": metrics.tasks_pending,
            "completion_rate": metrics.completion_rate,
            "completion_rate_change": metrics.completion_rate_change,
        },
        "overall_score": metrics.overall_score,
        "skills_summary": [{"skill": k, "level": v} for k, v in (metrics.skills_summary or {}).items()],
        "contributions_timeseries": metrics.contributions_timeseries or [],
        "last_updated": metrics.last_updated,
    }

@router.get("/org/{org_id}", response_model=schemas.OrgDashboardResponse, dependencies=[Depends(require_role("mentor"))])
def get_org_dashboard(org_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    org_metrics = services.get_cached_org_dashboard(db, org_id)
    if not org_metrics:
        org_metrics = services.compute_org_metrics(db, org_id)
    if not org_metrics:
        raise HTTPException(status_code=404, detail="Organization dashboard not found")
    return {
        "org_id": org_id,
        "team_members": org_metrics.team_members,
        "active_projects": org_metrics.active_projects,
        "tasks": {
            "completed": org_metrics.tasks_completed,
            "pending": org_metrics.tasks_pending,
            "unassigned": org_metrics.tasks_unassigned,
        },
        "team_performance": org_metrics.team_performance,
        "task_completion_trend": org_metrics.task_completion_trend,
        "project_summaries": org_metrics.project_summaries or {},
        "team_member_summary": org_metrics.team_member_summary or [],
        "active_blockers": org_metrics.active_blockers or [],
        "last_updated": org_metrics.last_updated,
    }