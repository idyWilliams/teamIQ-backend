from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate
from fastapi import HTTPException
from sqlalchemy import func

def get_tasks(db: Session, skip: int = 0, limit: int = 100, status: TaskStatus = None, user_id: int = None, org_id: int = None):
    query = db.query(Task).offset(skip).limit(limit)
    if status:
        query = query.filter(Task.status == status)
    if user_id:
        query = query.filter(Task.owner_id == user_id)
    if org_id:
        query = query.filter(Task.organization_id == org_id)
    return query.all()

def create_task(db: Session, task: TaskCreate, user_id: int = None, org_id: int = None):
    db_task = Task(**task.model_dump(), owner_id=user_id, organization_id=org_id)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task_status(db: Session, task_id: int, status: TaskStatus):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = status
    if status == TaskStatus.DONE:
        task.completed_at = func.now()
    else:
        task.completed_at = None
    db.commit()
    db.refresh(task)
    return task