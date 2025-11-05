from pydantic import BaseModel, EmailStr, field_validator, field_serializer
from app.models.organization import UserRole
import datetime
from typing import Optional, Dict, List, TYPE_CHECKING
import json
import re

# ✅ FIX: Import Organization only for type checking
if TYPE_CHECKING:
    from app.models.organization import Organization


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class OrganizationSignUp(BaseModel):
    """
    Step 1: Initial signup - minimal required fields
    """
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
    """
    Step 2+: For onboarding completion and profile updates
    """
    organization_name: Optional[str] = None
    team_size: Optional[str] = None
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[List[str]] = None
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

    @field_validator("domain_link")
    def validate_domain(cls, v):
        """Validate domain format for integrations"""
        if v is None:
            return v

        v = v.strip().lower()
        v = v.replace('https://', '').replace('http://', '').rstrip('/')

        if not '.' in v:
            raise ValueError(
                "Invalid domain format. Please provide a valid domain (e.g., yourcompany.com)"
            )

        domain_pattern = r'^[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,}$'
        if not re.match(domain_pattern, v):
            raise ValueError(
                "Invalid domain format. Use format: yourcompany.com"
            )

        return v

    @field_validator("website")
    def validate_website(cls, v):
        if v is None:
            return v
        if not v.startswith(('http://', 'https://')):
            v = f"https://{v}"
        return v

    @field_validator("phone_number")
    def validate_phone(cls, v):
        if v is None:
            return v
        clean = re.sub(r'[\s\-\(\)]', '', v)
        if not re.match(r'^\+?[1-9]\d{1,14}$', clean):
            raise ValueError(
                "Invalid phone number format. Use international format: +234xxx"
            )
        return v


class OrganizationOnboardingComplete(BaseModel):
    """
    Specific schema for onboarding completion (KYC)
    """
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: str
    favorite_tools: Optional[List[str]] = None
    website: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("domain_link")
    def validate_domain(cls, v):
        if not v or not v.strip():
            raise ValueError(
                "Domain is required to complete onboarding. "
                "This is needed for integration features."
            )

        v = v.strip().lower()
        v = v.replace('https://', '').replace('http://', '').rstrip('/')

        if not '.' in v:
            raise ValueError("Invalid domain format. Example: yourcompany.com")

        return v


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class OrganizationOut(BaseModel):
    """Organization response schema"""
    id: int
    organization_name: str
    team_size: str
    email: EmailStr
    role: UserRole
    organization_image: Optional[str] = None
    description: Optional[str] = None
    sector: Optional[str] = None
    social_media_handles: Optional[Dict[str, str]] = None
    domain_link: Optional[str] = None
    favorite_tools: Optional[List[str]] = None
    website: Optional[str] = None
    country: Optional[str] = None
    phone_number: Optional[str] = None
    createdAt: datetime.datetime
    updatedAt: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

    @field_serializer('createdAt')
    def serialize_created_at(self, dt: datetime.datetime, _info):
        return dt.isoformat() if dt else None

    @field_serializer('updatedAt')
    def serialize_updated_at(self, dt: datetime.datetime, _info):
        return dt.isoformat() if dt else None

    @field_serializer('role')
    def serialize_role(self, role: UserRole, _info):
        return role.value


class OrganizationProfileComplete(BaseModel):
    """Check if organization profile is complete"""
    is_complete: bool
    missing_fields: List[str]
    message: str

    @classmethod
    def from_organization(cls, org):  
        """Check which required fields are missing"""
        # Import at runtime to avoid circular dependency
        from app.models.organization import Organization

        required_for_integrations = [
            "domain_link",
            "description",
            "sector"
        ]

        missing = []
        for field in required_for_integrations:
            value = getattr(org, field, None)
            if not value:
                missing.append(field)

        is_complete = len(missing) == 0

        if is_complete:
            message = "Organization profile is complete. You can now create projects and configure integrations."
        else:
            message = f"Please complete your profile to enable all features. Missing: {', '.join(missing)}"

        return cls(
            is_complete=is_complete,
            missing_fields=missing,
            message=message
        )


class OrganizationStats(BaseModel):
    """Organization statistics for dashboard"""
    total_projects: int
    total_users: int
    active_integrations: int
    team_performance: float
