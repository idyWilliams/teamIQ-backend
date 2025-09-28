from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.api.users.models.user import User, Organization
import os
from dotenv import load_dotenv
from app.api.users.utils.email_utils import send_email
from app.api.users.schemas.user import PasswordResetRequest, PasswordResetConfirm
from app.api.users.utils.auth_utils import pwd_context
from app.api.users.utils.auth_utils import get_password_hash, create_reset_token, verify_reset_token
from app.db.database import get_db
from app.api.users.utils.auth_utils import ACCESS_TOKEN_EXPIRE_MINUTES, verify_password
from app.api.users.dependencies.auth import create_access_token
from app.api.crud.users import (
    create_user,
    get_user_by_email,
    create_organization,
    get_organization_by_name,
)
from app.api.users.schemas.user import (
    UserCreate,
    UserOut,
    OrganizationCreate,
    OrganizationOut,
    Token,
)
from app.api.users.models.user import UserRole

load_dotenv()

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# ---------------------------
# Register Individual
# ---------------------------
@router.post("/register/individual", response_model=UserOut)
def register_individual(user: UserCreate, db: Session = Depends(get_db)):
    db_user = create_user(db, user)
    return db_user  # ✅ serialized into UserOut


# ---------------------------
# Register Organization
# ---------------------------
@router.post("/register/organization", response_model=OrganizationOut)
def register_organization(organization: OrganizationCreate, db: Session = Depends(get_db)):
    db_org = create_organization(db, organization)
    return db_org  # ✅ serialized into OrganizationOut


# ---------------------------
# Login (works for both User + Organization)
# ---------------------------
@router.post("/login", response_model=Token)
def login(email: str, password: str, db: Session = Depends(get_db)):
    # Try user
    user = get_user_by_email(db, email)
    if user and verify_password(password, user.hashed_password):
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role.value},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    # Try organization
    org = get_organization_by_name(db, email)
    if org and verify_password(password, org.hashed_password):
        access_token = create_access_token(
            data={"sub": org.organization_name, "role": org.role.value},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email/organization or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Forgot Password for User
@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found with this email")
    token = create_reset_token(data.email)
    reset_link = f"http://localhost:8000/reset-password/{token}"
    await send_email(email=data.email, reset_link=reset_link)
    return {"Message": "Password reset link sent to email"}


# Reset Password for User 
@router.post("/reset-password/{token}")
async def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = verify_reset_token(data.token)
    if email:
        user = db.query(User).filter(User.email == email).first()
        hashed_password = get_password_hash(data.new_password)
        user.hashed_password = hashed_password
        db.commit()
        return {"message": "User password reset successful"}
    return 