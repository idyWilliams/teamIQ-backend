from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories import project_repository
from app.schemas.response_model import create_response

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = project_repository.create_project(db, project)
    return create_response(success=True, message="Project created successfully", data=ProjectResponse.from_orm(db_project).model_dump())

@router.get("/")
def list_projects(db: Session = Depends(get_db)):
    projects = project_repository.list_projects(db)
    return create_response(success=True, message="Projects retrieved successfully", data=[ProjectResponse.from_orm(p).model_dump() for p in projects])
