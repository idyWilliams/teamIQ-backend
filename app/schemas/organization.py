from pydantic import BaseModel, EmailStr, field_validator, model_validator, field_serializer
from app.models.organization import UserRole
import datetime
from typing import Optional, Dict
import json
import re


# --------------------
# Request Schemas
# --------------------
class OrganizationSignUp(BaseModel):
    """Initial signup - minimal required fields"""
    organization_name: str
    team_size: str
    email: EmailStr
    country: str
    password: str

    @field_validator("team_size")
    def valid_team_size(cls, v):
        allowed_sizes = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
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
            raise ValueError("Password must contain at least one special character")
        return v


class OrganizationUpdate(BaseModel):
    """For onboarding and profile updates - all fields optional"""
    organization_name: Optional[str] = None
    team_size: Optional[str] = None
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[Dict[str, str]] = None
    website: Optional[str] = None
    country: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("team_size")
    def valid_team_size(cls, v):
        if v is None:
            return v
        allowed_sizes = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
        return v


# --------------------
# Response Schemas
# --------------------
class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: str  # Changed from int to str
    email: EmailStr
    role: UserRole
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[Dict[str, str]] = None
    website: Optional[str] = None
    country: Optional[str] = None
    phone_number: Optional[str] = None
    createdAt: datetime.datetime

    class Config:
        from_attributes = True

    @field_serializer('createdAt')
    def serialize_dt(self, dt: datetime.datetime, _info):
        return dt.isoformat()

    @field_serializer('role')
    def serialize_role(self, role: UserRole, _info):
        return role.value
