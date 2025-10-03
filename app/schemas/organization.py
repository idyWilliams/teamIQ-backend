from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.organization import UserRole 

class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    email: Optional[EmailStr] = None
    password: str
    repeatpassword: str
    role: Optional[UserRole] = UserRole.ORGANIZATION

    @field_validator("repeatpassword")
    @classmethod
    def passwords_match(cls, v, values):
        if "password" in values.data and v != values.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("team_size")
    @classmethod
    def valid_team_size(cls, v):
        allowed_sizes = [2, 3, 5, 8, 10, 15, 20, 50, 100]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
        return v


class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
    email: Optional[EmailStr] = None
    role: str

    class Config:
        from_attributes = True  # replaces orm_mode=True
