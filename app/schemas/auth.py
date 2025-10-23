from pydantic import BaseModel, EmailStr
from typing import Optional
from app.schemas.user import UserOut
from app.schemas.organization import OrganizationOut


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
    remember_me: bool = False
