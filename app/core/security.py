from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from typing import TYPE_CHECKING
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories import user_repository, organization_repository
from app.core.config import settings


if TYPE_CHECKING:
    pass

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
SECRET_KEY = settings.SECRET_KEY

oauth2_scheme = HTTPBearer()


def create_access_token(data: dict, expires_delta: timedelta | None = None, entity_type: str = "user"):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "entity_type": entity_type})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_reset_token(email: str):
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")


def get_current_user_or_organization(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Returns either User or Organization based on token"""


    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        entity_type: str = payload.get("entity_type", "user")

        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if entity_type == "organization":
        organization = organization_repository.get_organization_by_email(db, email=email)
        if organization:
            print("Returning organization from get_current_user_or_organization")
            print(organization.__dict__)
            organization.entity_type = "organization"
            return organization
    elif entity_type == "user":
        user = user_repository.get_user_by_email(db, email=email)
        if user:
            user.entity_type = "user"
            return user
    else:  # Fallback for older tokens without entity_type
        user = user_repository.get_user_by_email(db, email=email)
        if user:
            user.entity_type = "user"
            return user

        organization = organization_repository.get_organization_by_email(db, email=email)
        if organization:
            organization.entity_type = "organization"
            return organization

    raise credentials_exception


def get_current_organization(
    current_user = Depends(get_current_user_or_organization)
):
    """Ensures current user is an Organization"""

    from app.models.organization import Organization

    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can perform this action")
    return current_user
