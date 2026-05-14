from pydantic import BaseModel
import datetime
from app.models.task import TaskStatus, TaskPriority
from typing import Optional, List


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    due_date: Optional[datetime.datetime] = None
    tags: Optional[List[str]] = None


class TaskCreate(TaskBase):
    project_id: Optional[int] = None
    owner_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime.datetime] = None
    owner_id: Optional[int] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase):
    id: int
    display_task_id: Optional[str] = None # e.g. #TSK-123
    owner_id: Optional[int]
    organization_id: Optional[int]
    project_id: Optional[int]
    
    # UI styling
    status_color: Optional[str] = None
    category_color: Optional[str] = None
    
    # Assignment
    assignees: List[dict] = [] # List of user objects with avatars

    # Engagement
    attachment_count: int = 0
    message_count: int = 0
    file_count: int = 0

    # External sync fields
    external_id: Optional[str]
    external_source: Optional[str]
    external_url: Optional[str]
    last_synced_at: Optional[datetime.datetime]

    completed_at: Optional[datetime.datetime]
    createdAt: datetime.datetime
    updatedAt: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class TaskWithHistory(TaskResponse):
    """Task with change history for detailed view"""
    history: List[dict] = []
    comments: List[dict] = []


class TaskMoveRequest(BaseModel):
    """Request to move task between statuses (Kanban drag-drop)"""
    new_status: TaskStatus
    position: Optional[int] = None  # For ordering within column
