from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.task import Task, TaskCreate
from app.repositories import task_repository
from app.schemas.response_model import create_response
# from app.core.security import get_current_user # Will be added later
# from app.schemas.user import User # Will be added later

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/")
def create_task_for_user(task: TaskCreate, db: Session = Depends(get_db)):
    # This is a placeholder. In a real app, you'd get the user from the token.
    fake_user_id = 1 
    db_task = task_repository.create_task(db=db, task=task, user_id=fake_user_id)
    return create_response(success=True, message="Task created successfully", data=Task.from_orm(db_task).model_dump())

@router.get("/")
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = task_repository.get_tasks(db, skip=skip, limit=limit)
    return create_response(success=True, message="Tasks retrieved successfully", data=[Task.from_orm(t).model_dump() for t in tasks])