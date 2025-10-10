from pydantic import BaseModel
import datetime

class ProjectCreate(BaseModel):
    name: str
    owner_id: int

class ProjectResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    createdAt: datetime.datetime

    class Config:
        from_attributes = True
