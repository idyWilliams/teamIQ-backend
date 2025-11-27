from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dashboard import DashboardResponse, OrgDashboardResponse
from app.services.dashboard_service import compute_and_upsert_dashboard_metrics, get_cached_org_dashboard, compute_org_metrics
from app.core.security import get_current_user_or_organization
from app.schemas.response_model import create_response
from app.models.user import User
from app.models.organization import Organization

from app.models.project import Project
from app.models.task import Task
from app.models.activity import Activity

router = APIRouter()

@router.get("/user")
def get_user_dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Access denied for organizations")
    metrics = compute_and_upsert_dashboard_metrics(db, current_user.id)
    return create_response(
        success=True,
        message="User dashboard retrieved successfully",
        data=DashboardResponse.model_validate(metrics)
    )

@router.get("/organization")
def get_org_dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Access denied for users")
    metrics = compute_org_metrics(db, current_user.id) or get_cached_org_dashboard(db, current_user.id)
    if not metrics:
        metrics = OrgDashboardResponse(org_id=current_user.id)
        db.add(metrics)
        db.commit()
    return create_response(
        success=True,
        message="Organization dashboard retrieved successfully",
        data=OrgDashboardResponse.model_validate(metrics)
    )

@router.get("/project/{project_id}")
def get_project_dashboard(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get dashboard metrics for a specific project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Compute metrics
    total_tasks = db.query(Task).filter(Task.project_id == project_id).count()
    completed_tasks = db.query(Task).filter(Task.project_id == project_id, Task.status == "done").count()

    recent_activities = db.query(Activity).filter(
        Activity.project_id == project_id
    ).order_by(Activity.created_at.desc()).limit(10).all()

    metrics = {
        "project_id": project.id,
        "project_name": project.name,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
        "recent_activities": recent_activities
    }

    return create_response(
        success=True,
        message="Project dashboard retrieved successfully",
        data=metrics
    )