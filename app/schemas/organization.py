from pydantic import BaseModel, EmailStr
from app.models.organization import UserRole
import datetime

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: EmailStr
    password: str

class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
    email: EmailStr
    role: UserRole
    createdAt: datetime.datetime

    class Config:
        from_attributes = True
