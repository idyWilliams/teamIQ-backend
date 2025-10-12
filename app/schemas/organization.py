from pydantic import BaseModel, EmailStr
from app.models.organization import UserRole
import datetime
from typing import Optional, Dict

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: EmailStr
    password: str
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[Dict[str, str]] = None
    website: Optional[str] = None
    address: Optional[str] = None
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
    address: Optional[str] = None
    phone_number: Optional[str] = None
    createdAt: datetime.datetime

    class Config:
        from_attributes = True
