from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories import project_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    db_project = project_repository.create_project(db, project)
    project_out = ProjectResponse.from_orm(db_project)
    project_out.createdAt = db_project.createdAt
    return create_response(success=True, message="Project created successfully", data=project_out.model_dump())

@router.get("/")
def list_projects(db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    projects = project_repository.list_projects(db)
    projects_out = []
    for p in projects:
        project_out = ProjectResponse.from_orm(p)
        project_out.createdAt = p.createdAt
        projects_out.append(project_out)
    return create_response(success=True, message="Projects retrieved successfully", data=[p.model_dump() for p in projects_out])
