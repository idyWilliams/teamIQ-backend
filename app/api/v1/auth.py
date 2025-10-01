# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
import logging

from app.schemas.user import UserCreate, UserOut, Token
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.core.security import verify_password, create_access_token
from app.repositories import user_repository, organization_repository
from app.core.database import get_db
from app.models.user import User, UserRole

# OAuth (keeps your Google login)
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from app.core.config import settings
from app.models.user import User, UserRole
import logging
logger = logging.getLogger("app_logger")

logger.info("This is an info log!", extra={"module": "user_service"})
logger.error("This is an error log!", extra={"error": "something bad happened"})


router = APIRouter(tags=["auth"])

# OAuth setup (uses settings from your config)
config = Config(environ={
    "GITHUB_CLIENT_ID": settings.GITHUB_CLIENT_ID,
    "GITHUB_CLIENT_SECRET": settings.GITHUB_CLIENT_SECRET,
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
    "MICROSOFT_CLIENT_ID": settings.MICROSOFT_CLIENT_ID,
    "MICROSOFT_CLIENT_SECRET": settings.MICROSOFT_CLIENT_SECRET
})
oauth = OAuth(config)

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://www.googleapis.com/oauth2/v3/userinfo",
    client_kwargs={"scope": "openid email profile"},
)


# -------------------------
# Registration endpoints
# -------------------------
@router.post("/register/individual", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_individual(user: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Create an individual user.
    """
    existing = user_repository.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    try:
        db_user = user_repository.create_user(db, user)
        return db_user
    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/register/organization", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def register_organization(organization: OrganizationCreate, db: Session = Depends(get_db)):
    logger.info(f"Received organization data: {organization.dict()}")
    logger.info(f"Using UserRole enum: {[(e.name, e.value) for e in UserRole]}")
    if organization_repository.get_organization_by_name(db, organization.organization_name):
        raise HTTPException(status_code=400, detail="Organization with this name already exists")
    if getattr(organization, "email", None):
        if organization_repository.get_organization_by_email(db, organization.email):
            raise HTTPException(status_code=400, detail="Organization with this email already exists")
    try:
        db_org = organization_repository.create_organization(db, organization)
        logger.info(f"Created organization: {db_org.organization_name}, role: {db_org.role}")
        return db_org
    except Exception as e:
        logger.error(f"Error creating organization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



# -------------------------
# Login endpoints
# -------------------------
@router.post("/login/individual", response_model=Token)
def login_individual(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """
    Login for individual users.
    Use content-type application/x-www-form-urlencoded (OAuth2PasswordRequestForm).
    """
    user = user_repository.get_user_by_email(db, form_data.username)
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/organization", response_model=Token)
def login_organization(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """
    Login for organizations (username can be organization_name or email).
    Use content-type application/x-www-form-urlencoded.
    """
    org = organization_repository.get_organization_by_name(db, form_data.username)
    if not org:
        org = organization_repository.get_organization_by_email(db, form_data.username)

    if not org or not org.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect organization name/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, org.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect organization name/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(org.id), "role": org.role.value})
    return {"access_token": access_token, "token_type": "bearer"}


# -------------------------
# Google OAuth endpoints
# -------------------------
@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth:google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google", name="google_callback")
async def callback_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = await oauth.google.get("userinfo", token=token)
        info = user_info.json()
        email = info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Google email not provided")

        user = user_repository.get_user_by_email(db, email)
        if not user:
            new_user = User(
                email=email,
                username=email.split("@")[0],
                first_name=info.get("given_name", ""),
                last_name=info.get("family_name", ""),
                country="Unknown",
                hashed_password=None,
                role=UserRole.INTERN,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user = new_user

        access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
