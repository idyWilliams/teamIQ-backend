from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, field_serializer
from typing import Optional
from app.models.organization import UserRole
import datetime
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


# --------------------
# Response Schemas
# --------------------
class UserOut(BaseModel):
    """Response schema for users"""
    id: int
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    country: str
    role: UserRole
    profile_image: Optional[str] = None
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    organization_id: Optional[int] = None
    createdAt: datetime.datetime

    class Config:
        from_attributes = True

    @field_serializer('createdAt')
    def serialize_dt(self, dt: datetime.datetime, _info):
        return dt.isoformat()

    @field_serializer('role')
    def serialize_role(self, role: UserRole, _info):
        return role.value
