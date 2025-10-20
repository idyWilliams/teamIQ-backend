from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.schemas.task import Task, TaskCreate
from app.repositories import task_repository
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
