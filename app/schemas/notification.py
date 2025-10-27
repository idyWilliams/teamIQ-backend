from pydantic import BaseModel
from typing import Optional
import datetime

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
    createdAt: datetime.datetime

    class Config:
        # support .from_orm() and pydantic v2 from_attributes
        orm_mode = True
        from_attributes = True
