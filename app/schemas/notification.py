from pydantic import BaseModel
from typing import Optional
import datetime  # Added for createdAt field

class NotificationCreate(BaseModel):
    title: str
    message: str
    type: Optional[str] = "info"

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    type: str
    createdAt: datetime.datetime  # Now resolves with import
<<<<<<< HEAD
from datetime import datetime
from typing import Optional
from app.models.notification import NotificationType

class NotificationBase(BaseModel):
    type: NotificationType
    message: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationOut(NotificationBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationPreferenceBase(BaseModel):
    task_assigned_email: bool = True
    task_updated_email: bool = True
    project_completed_email: bool = True
    daily_summary_email: bool = True
    task_assigned_slack: bool = False
    task_updated_slack: bool = False
    project_completed_slack: bool = False

class NotificationPreferenceCreate(NotificationPreferenceBase):
    user_id: int

class NotificationPreferenceOut(NotificationPreferenceBase):
    id: int
    user_id: int
=======
from typing import Optional
import datetime  # Added for createdAt field

class NotificationCreate(BaseModel):
    title: str
    message: str
    type: Optional[str] = "info"

class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    type: str
    createdAt: datetime.datetime  # Now resolves with import
>>>>>>> origin/staging

    class Config:
        from_attributes = True