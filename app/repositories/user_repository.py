from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, Organization, UserRole
from app.schemas.user import UserCreate, OrganizationCreate
from app.core.security import get_password_hash


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_organization_by_name(db: Session, name: str):
    return db.query(Organization).filter(Organization.organization_name == name).first()


def create_user(db: Session, user: UserCreate):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    print(db_user)
    try:
        hashed_pw = get_password_hash(user.password)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long (must be ≤ 72 characters)."
        )

    new_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        country=user.country,
        hashed_password=hashed_pw,
        role=UserRole.INTERN
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def create_organization(db: Session, organization: OrganizationCreate):
    db_org = get_organization_by_name(db, organization.organization_name)
    if db_org:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization already registered")

    hashed_pw = get_password_hash(organization.password)
    new_org = Organization(
        organization_name=organization.organization_name,
        team_size=organization.team_size,
        hashed_password=hashed_pw,
        role=UserRole.ORGANIZATION
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    return new_org