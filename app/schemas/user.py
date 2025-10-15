from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo, model_validator
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

# ... (Keep all existing classes unchanged until OrganizationOut)

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

    @model_validator(mode='before')
    def parse_json_fields(cls, values):
        # Handle both dict (payload) and ORM object (DB load)
        if hasattr(values, '__dict__'):  # ORM object
            values = values.__dict__.copy()  # Extract attrs to dict
        if not isinstance(values, dict):
            values = {}  # Fallback
        
        # Parse JSON strings to dicts
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

