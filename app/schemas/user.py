from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, field_serializer
from typing import Optional
from app.models.organization import UserRole
import datetime
import re  # For password regex validation
import json  # For JSON parsing in validator

# --------------------
# Request Schemas
# --------------------
class UserCreate(BaseModel):
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

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: EmailStr
    password: str
    repeatpassword: str
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[dict[str, str]] = None
    website: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("repeatpassword")
    def passwords_match(cls, v: str, info: ValidationInfo):
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("team_size")
    def valid_team_size(cls, v):
        allowed_sizes = [2, 3, 5, 8, 10, 15, 20, 50, 100]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
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

# --------------------
# Response Schemas
# --------------------
class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    country: str
    role: UserRole
    createdAt: datetime.datetime
    organization_id: Optional[int] = None

    class Config:
        from_attributes = True

    @field_serializer('createdAt')
    def serialize_dt(self, dt: datetime.datetime, _info):
        return dt.isoformat()

    @field_serializer('role')
    def serialize_role(self, role: UserRole, _info):
        return role.value


class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
    email: EmailStr
    role: UserRole
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[dict[str, str]] = None
    website: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    createdAt: datetime.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional[UserOut] = None
    organization: Optional[OrganizationOut] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False  # No validation—verifies hash only

