from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.organization import UserRole
import datetime

class InvitationCreate(BaseModel):
    email: EmailStr
    role: UserRole
    stack: Optional[str] = None

class InvitationOut(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    stack: Optional[str] = None
    invitation_code: str
    expires_at: datetime.datetime
    accepted: bool
    organization_id: int
    createdAt: datetime.datetime

    class Config:
        from_attributes = True