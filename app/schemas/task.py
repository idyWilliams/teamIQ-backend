from pydantic import BaseModel
import datetime
from app.models.task import TaskStatus
from typing import Optional

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None

class Task(TaskBase):
    id: int
    owner_id: Optional[int]
    organization_id: Optional[int]
    status: TaskStatus
    completed_at: Optional[datetime.datetime]
    createdAt: datetime.datetime

    class Config:
        from_attributes = True