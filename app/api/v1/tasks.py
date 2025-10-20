<<<<<<< HEAD
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
=======
from fastapi import APIRouter, Depends, HTTPException
>>>>>>> origin/staging
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.schemas.task import Task, TaskCreate, TaskUpdate
from app.schemas.notification import NotificationCreate
from app.repositories import task_repository
<<<<<<< HEAD
from app.services.notification_service import trigger_notification
# from app.core.security import get_current_user  # For future authentication
# from app.schemas.user import User               # For future user schema

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task_for_user(
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new task and send notification to the owner.
    """
    try:
        # Temporary user placeholder — replace with authenticated user later
        fake_user_id = 1  

        # Create the task using repository pattern
        db_task = task_repository.create_task(db=db, task=task, user_id=fake_user_id)

        # Trigger notification in background
        trigger_notification(
            db,
            fake_user_id,
            "task_assigned",
            f"New task assigned: {task.title}",
            background_tasks
        )
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@router.get("/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get a list of all tasks (paginated).
    """
    try:
        tasks = task_repository.get_tasks(db, skip=skip, limit=limit)
        return tasks
    except Exception as e:
        logger.error(f"Error reading tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")


@router.put("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    task: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Update an existing task and notify the owner.
    """
    try:
        db_task = task_repository.update_task(db=db, task_id=task_id, task=task)
        if not db_task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Send notification
        trigger_notification(
            db,
            db_task.owner_id,
            "task_updated",
            f"Task updated: {db_task.title}",
            background_tasks
        )
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task")
=======
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from app.models.task import TaskStatus

router = APIRouter(tags=["tasks"])

@router.post("/")
def create_task_for_user(task: TaskCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    db_task = task_repository.create_task(db=db, task=task, user_id=user_id, org_id=org_id)
    task_out = Task.model_validate(db_task)
    return create_response(success=True, message="Task created successfully", data=task_out.model_dump())

@router.get("/", response_model=List[Task])
def read_tasks(status: TaskStatus = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    tasks = task_repository.get_tasks(db, skip=skip, limit=limit, status=status, user_id=user_id, org_id=org_id)
    tasks_out = [Task.model_validate(t) for t in tasks]
    return create_response(success=True, message="Tasks retrieved successfully", data=[t.model_dump() for t in tasks_out]).data

@router.patch("/{task_id}/status")
def update_task_status(task_id: int, update: TaskUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    # Auth check (owner or org)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    if task.owner_id != user_id and task.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated_task = task_repository.update_task_status(db, task_id, update.status)
    task_out = Task.model_validate(updated_task)
    # Create notification
    from app.repositories.notification_repository import create_notification
    create_notification(db, NotificationCreate(title="Task Updated", message=f"Status changed to {update.status.value}"), user_id=user_id)
    return create_response(success=True, message="Task updated", data=task_out.model_dump())
>>>>>>> origin/staging
