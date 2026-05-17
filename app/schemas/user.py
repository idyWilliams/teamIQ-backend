from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, field_serializer
from typing import Optional

from app.models.organization import UserRole
from datetime import datetime, timezone, timedelta
import re


# --------------------
# Request Schemas
# --------------------
class UserCreate(BaseModel):
    """User registration schema"""
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    country: str
    role: Optional[UserRole] = UserRole.INTERN
    password: str
    repeatpassword: str

    @field_validator("repeatpassword")
    def passwords_match(cls, v: str, info: ValidationInfo):
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("password")
    def validate_password(cls, v: str):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;':\",./<>?]", v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;':\",./<>?)")
        return v


class UserUpdate(BaseModel):
    """User profile update schema - all fields optional"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    country: Optional[str] = None
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    track: str
    stacks: list[str]


# --------------------
# Response Schemas
# --------------------
class UserSkillOut(BaseModel):
    name: str
    proficiency_score: float # 0-100

    class Config:
        from_attributes = True

class UserOut(BaseModel):
    """Response schema for users"""
    id: int
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    country: str
    role: UserRole
    job_title: Optional[str] = None # Maps to track
    profile_image: Optional[str] = None
    avatar_url: Optional[str] = None # Alias for profile_image
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    organization_id: Optional[int] = None
    createdAt: datetime
    last_seen: Optional[datetime] = None
    onboarding_completed: bool = False
    online_status: str = "offline" # "online" or "offline"
    skills: list[UserSkillOut] = []

    class Config:
        from_attributes = True

    @property
    def is_online(self) -> bool:
        if self.last_seen:
            # Handle both aware and naive datetimes by converting to UTC
            now = datetime.now(timezone.utc)
            ls = self.last_seen
            if ls.tzinfo is None:
                ls = ls.replace(tzinfo=timezone.utc)
            return (now - ls) < timedelta(minutes=5)
        return False

    @field_serializer('createdAt')
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()

    @field_serializer('last_seen')
    def serialize_last_seen(self, dt: Optional[datetime], _info):
        return dt.isoformat() if dt else None

    @field_serializer('role')
    def serialize_role(self, role: UserRole, _info):
        return role.value
