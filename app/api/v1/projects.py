from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories import project_repository
<<<<<<< HEAD
from app.services.notification_service import trigger_notification

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.
    """
    return project_repository.create_project(db, project)


@router.get("/", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """
    Get a list of all projects.
    """
    return project_repository.list_projects(db)


@router.put("/{project_id}/complete", response_model=ProjectResponse)
def complete_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Mark a project as completed and notify all mentors.
    """
    try:
        project = project_repository.get_project_by_id(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update project status
        project.is_completed = True
        db.commit()
        db.refresh(project)

        # Notify mentors in background
        mentors = project_repository.get_mentors(db)
        for mentor in mentors:
            trigger_notification(
                db,
                mentor.id,
                "project_completed",
                f"Project completed: {project.title}",
                background_tasks
            )

        return project
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing project: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete project")
=======
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
>>>>>>> origin/staging
