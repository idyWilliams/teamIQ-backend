from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from app.models.organization import UserRole

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

    @validator("repeatpassword")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class OrganizationCreate(BaseModel):
    organization_name: str
    team_size: int
    password: str
    repeatpassword: str

    @validator("repeatpassword")
    def passwords_match(cls, v, values, **kwargs):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("team_size")
    def valid_team_size(cls, v):
        allowed_sizes = [2, 3, 5, 8, 10, 15, 20, 50, 100]
        if v not in allowed_sizes:
            raise ValueError(f"Team size must be one of {allowed_sizes}")
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

    class Config:
        orm_mode = True  # ✅ allows returning SQLAlchemy models directly


class OrganizationOut(BaseModel):
    id: int
    organization_name: str
    team_size: int
    role: UserRole

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
