from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.core.hashing import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email.lower()).first()  # Fixed: Lowercase for case-insensitivity

def get_users_by_organization(db: Session, organization_id: int):
    return db.query(User).filter(User.organization_id == organization_id).all()

def create_user(db: Session, user: UserCreate, organization_id: int = None):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_pw = get_password_hash(user.password)

    new_user = User(
        email=user.email.lower(),  # Fixed: Store lowercase
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        country=user.country,
        hashed_password=hashed_pw,
        role=UserRole.INTERN,
        organization_id=organization_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user