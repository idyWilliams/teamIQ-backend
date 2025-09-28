from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.users.schemas.user import UserCreate, UserOut, OrganizationCreate, OrganizationOut, Token
from app.api.users.utils.auth_utils import verify_password
import secrets
from datetime import datetime, timedelta

from app.api.crud.users import (
    create_user,
    get_user_by_email,
    create_organization,
    get_organization_by_name,
)
from app.db.database import get_db
from app.api.users.dependencies.auth import create_access_token
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.api.config import settings
from app.api.users.models.user import User, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth setup
config = Config(environ={
    "GITHUB_CLIENT_ID": settings.GITHUB_CLIENT_ID,
    "GITHUB_CLIENT_SECRET": settings.GITHUB_CLIENT_SECRET,
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
    "MICROSOFT_CLIENT_ID": settings.MICROSOFT_CLIENT_ID,
    "MICROSOFT_CLIENT_SECRET": settings.MICROSOFT_CLIENT_SECRET
})

oauth = OAuth(config)

# Google OAuth
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://www.googleapis.com/oauth2/v3/userinfo",
    client_kwargs={"scope": "openid email profile"}
)


@router.post("/register/individual", response_model=UserOut)
def register_individual(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = create_user(db, user)
        return db_user  # ✅ FastAPI will convert via orm_mode -> UserOut
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/register/organization", response_model=OrganizationOut)
def register_organization(organization: OrganizationCreate, db: Session = Depends(get_db)):
    try:
        db_organization = create_organization(db, organization)
        return db_organization  # ✅ serialized via orm_mode -> OrganizationOut
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try User table first
    user = get_user_by_email(db, form_data.username)
    if user and verify_password(form_data.password, user.hashed_password):
        access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
        return {"access_token": access_token, "token_type": "bearer"}

    # Try Organization table
    organization = get_organization_by_name(db, form_data.username)
    if organization and verify_password(form_data.password, organization.hashed_password):
        access_token = create_access_token(data={"sub": organization.organization_name, "role": organization.role.value})
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email/organization name or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google", name="google_callback")
async def callback_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.get("userinfo", token=token)
        email = user_info.json().get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google email not provided")

        user = get_user_by_email(db, email)
        if not user:
            user = User(
                email=email,
                username=email.split("@")[0],
                first_name=user_info.json().get("given_name", ""),
                last_name=user_info.json().get("family_name", ""),
                country="Unknown",
                hashed_password=None,
                role=UserRole.INTERN,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


