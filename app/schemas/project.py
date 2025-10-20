from pydantic import BaseModel
import datetime
from typing import Optional

class ProjectCreate(BaseModel):
    name: str
    owner_id: int
    organization_id: Optional[int] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    organization_id: Optional[int]
    status: str  # From enum
    pct_complete: float
    createdAt: datetime.datetime

    class Config:
        from_attributes = True