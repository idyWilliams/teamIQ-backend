from fastapi import APIRouter, Depends, HTTPException
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
