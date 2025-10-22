from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dashboard import DashboardResponse, OrgDashboardResponse, OrgDashboardMetrics
from app.services.dashboard_service import compute_and_upsert_dashboard_metrics, get_cached_org_dashboard, compute_org_metrics
from app.core.security import get_current_user_or_organization
from app.schemas.response_model import create_response
from app.models.user import User
from app.models.organization import Organization

router = APIRouter(tags=["dashboard"])

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
        metrics = OrgDashboardMetrics(org_id=current_user.id)
        db.add(metrics)
        db.commit()
    return create_response(
        success=True,
        message="Organization dashboard retrieved successfully",
        data=OrgDashboardResponse.model_validate(metrics)
    )