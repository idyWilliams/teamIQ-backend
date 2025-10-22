from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, root_validator
from app.models.organization import UserRole
import datetime
from typing import Optional, Dict
import json

class OrganizationSignUp(BaseModel):
    organization_name: str
    team_size: str
    email: EmailStr
    country: str
    password: str

    @field_validator("team_size")
    def valid_team_size(cls, v):
        # mk this as range-limited
        allowed_sizes = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
        return v

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: str
    email: EmailStr
    password: str
    country: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("repeatpassword")
    def passwords_match(cls, v: str, info: ValidationInfo):
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("team_size")
    def valid_team_size(cls, v):
        # mk this as range-limited
        allowed_sizes = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
        return v

class OrganizationUpdate(BaseModel):
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


class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
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

    @root_validator(pre=True)
    def parse_json_fields(cls, values):
        # Force parse JSON strings to dicts (handles DB load as str)
        for field in ['social_media_handles', 'favorite_tools']:
            val = getattr(values, field, None)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        setattr(values, field, parsed)
                    else:
                        setattr(values, field, {})
                except (json.JSONDecodeError, TypeError):
                    setattr(values, field, {})
            elif val is None:
                setattr(values, field, {})
        return values