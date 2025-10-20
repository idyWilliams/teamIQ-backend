from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.repositories import project_repository
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
