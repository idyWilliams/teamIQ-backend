from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from app.models.organization import UserRole
import datetime


class InvitationCreate(BaseModel):
    email: EmailStr
    role: UserRole
    track: Optional[str] = None


class InvitationOut(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    track: Optional[str] = None
    invitation_code: str
    expires_at: datetime.datetime
    accepted: bool
    organization_id: int
    createdAt: datetime.datetime
    invite_link: Optional[str] = None

    # ✅ Pydantic v2 compatible config
    model_config = ConfigDict(from_attributes=True)


class InvitationOutWithStatus(InvitationOut):
    status: str
    accepted_at: Optional[datetime.datetime] = None

    @property
    def expires_in(self) -> Optional[datetime.timedelta]:
        if self.expires_at:
            return self.expires_at - datetime.datetime.now(datetime.timezone.utc)
        return None
