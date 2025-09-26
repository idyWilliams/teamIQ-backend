from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

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
