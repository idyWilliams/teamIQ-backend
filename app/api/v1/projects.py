from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories import project_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from app.models.project import ProjectStatus

router = APIRouter(tags=["projects"])

@router.post("/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    db_project = project_repository.create_project(db, project, org_id=org_id)
    project_out = ProjectResponse.model_validate(db_project)
    return create_response(success=True, message="Project created successfully", data=project_out.model_dump())

@router.get("/", response_model=List[ProjectResponse])
def list_projects(status: str = ProjectStatus.ACTIVE.value, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    projects = project_repository.list_projects(db, user_id=user_id, org_id=org_id, status=ProjectStatus(status))
    projects_out = [ProjectResponse.model_validate(p) for p in projects]
    return create_response(success=True, message="Projects retrieved successfully", data=[p.model_dump() for p in projects_out]).data