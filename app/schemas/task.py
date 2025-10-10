from pydantic import BaseModel
import datetime

class TaskBase(BaseModel):
    title: str
    description: str | None = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    owner_id: int
    createdAt: datetime.datetime

    class Config:
        from_attributes = True
