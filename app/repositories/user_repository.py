from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.models.stack import Stack
from app.models.user_stack import UserStack
from app.core.hashing import get_password_hash


def update_user_stacks(db: Session, user: User, stack_names: list[str]):
    """Update user's tech stack"""
    # Clear existing stacks for the user
    db.query(UserStack).filter(UserStack.user_id == user.id).delete()

    for stack_name in stack_names:
        stack = db.query(Stack).filter(Stack.name == stack_name).first()
        if not stack:
            stack = Stack(name=stack_name)
            db.add(stack)
            db.flush()

        user_stack = UserStack(user_id=user.id, stack_id=stack.id)
        db.add(user_stack)


def get_user_by_email(db: Session, email: str):
    """Get user by email (case-insensitive)"""
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_username(db: Session, username: str):
    """Get user by username (case-insensitive)"""
    return db.query(User).filter(User.username == username).first()


def get_users_by_organization(db: Session, organization_id: int):
    """Get all users belonging to an organization via many-to-many"""
    from app.models.organization import Organization

    # Query users through the many-to-many relationship
    return db.query(User).join(User.organizations).filter(
        Organization.id == organization_id
    ).all()


def create_user(db: Session, user: UserCreate, organization_id: int = None):
    """
    Create a new user without committing.

    Args:
        db: Database session
        user: User creation schema
        organization_id: Optional organization ID (NOT USED for many-to-many)

    Returns:
        User object (not yet committed/flushed)
    """
    # Check if email already exists
    db_user_by_email = get_user_by_email(db, user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if username already exists
    db_user_by_username = get_user_by_username(db, user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Hash the password (NOW THIS WORKS!)
    hashed_pw = get_password_hash(user.password)  

    # Create new user instance
    new_user = User(
        email=user.email.lower(),
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        country=user.country,
        hashed_password=hashed_pw,
        role=user.role if user.role else UserRole.INTERN,

    )

    db.add(new_user)


    return new_user


def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: int, update_data: dict):
    """Update user details"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    for key, value in update_data.items():
        if hasattr(user, key):
            setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user
