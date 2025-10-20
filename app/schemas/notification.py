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

    class Config:
        from_attributes = True