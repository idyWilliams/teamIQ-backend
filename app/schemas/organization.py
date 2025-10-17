from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, root_validator
from app.models.organization import UserRole
import datetime
from typing import Optional, Dict
import json

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: EmailStr
    password: str
    repeatpassword: str
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[Dict[str, str]] = None
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
        # mk this as range-limited
        allowed_sizes = [2, 3, 5, 8, 10, 15, 20, 50, 100]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
        return v

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
    address: Optional[str] = None
    phone_number: Optional[str] = None
    createdAt: datetime.datetime

    class Config:
        from_attributes = True

    @root_validator(pre=True)
    def parse_json_fields(cls, values):
        # Force parse JSON strings to dicts (handles DB load as str)
        for field in ['social_media_handles', 'favorite_tools']:
            val = values.get(field)
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        values[field] = parsed
                    else:
                        values[field] = {}
                except (json.JSONDecodeError, TypeError):
                    values[field] = {}
            elif val is None:
                values[field] = {}
        return values