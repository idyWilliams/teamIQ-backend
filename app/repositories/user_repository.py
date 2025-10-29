from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.core.hashing import get_password_hash


def get_user_by_email(db: Session, email: str):
    """Get user by email (case-insensitive)"""
    return db.query(User).filter(User.email == email.lower()).first()


def get_users_by_organization(db: Session, organization_id: int):
    """Get all users belonging to an organization"""
    return db.query(User).filter(User.organization_id == organization_id).all()


def create_user(db: Session, user: UserCreate, organization_id: int = None):
    """
    Create a new user without committing.

    Args:
        db: Database session
        user: User creation schema
        organization_id: Optional organization ID to associate with user

    Returns:
        User object (not yet committed/flushed)
    """
    # Check if email already exists
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password
    hashed_pw = get_password_hash(user.password)

    # Create new user instance
    new_user = User(
        email=user.email.lower(),
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        country=user.country,
        hashed_password=hashed_pw,
        role=user.role if user.role else UserRole.INTERN,  # Use provided role or default to INTERN
        organization_id=organization_id,
    )

    db.add(new_user)
    # Don't commit or flush here - let the caller control the transaction

    return new_user
