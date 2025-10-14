from pydantic import BaseModel, EmailStr, field_validator, ValidationInfo
from typing import Optional
from app.models.organization import UserRole
import datetime
from app.models.user import User as UserModel  # Avoid conflict

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

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: EmailStr  # Added missing
    password: str
    repeatpassword: str
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[dict] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[dict] = None
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

class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
    email: EmailStr
    role: UserRole
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[dict] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[dict] = None
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