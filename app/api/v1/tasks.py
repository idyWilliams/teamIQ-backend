from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.task import Task, TaskCreate
from app.repositories import task_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/")
def create_task_for_user(task: TaskCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    db_task = task_repository.create_task(db=db, task=task, user_id=current_user.id)
    task_out = Task.from_orm(db_task)
    task_out.createdAt = db_task.createdAt
    return create_response(success=True, message="Task created successfully", data=task_out.model_dump())

@router.get("/")
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    tasks = task_repository.get_tasks(db, skip=skip, limit=limit)
    tasks_out = []
    for t in tasks:
        task_out = Task.from_orm(t)
        task_out.createdAt = t.createdAt
        tasks_out.append(task_out)
    return create_response(success=True, message="Tasks retrieved successfully", data=[t.model_dump() for t in tasks_out])