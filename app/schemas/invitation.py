from pydantic import BaseModel, EmailStr, ConfigDict
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

    # ✅ Pydantic v2 compatible config
    model_config = ConfigDict(from_attributes=True)
