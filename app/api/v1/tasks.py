from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.task import Task, TaskCreate
from app.repositories import task_repository
# from app.core.security import get_current_user # Will be added later
# from app.schemas.user import User # Will be added later

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=Task)
def create_task_for_user(task: TaskCreate, db: Session = Depends(get_db)):
    # This is a placeholder. In a real app, you'd get the user from the token.
    fake_user_id = 1 
    return task_repository.create_task(db=db, task=task, user_id=fake_user_id)

@router.get("/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = task_repository.get_tasks(db, skip=skip, limit=limit)
    return tasks