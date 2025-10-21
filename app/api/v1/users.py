from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.organization import Organization
from app.schemas.user import UserOut
from app.repositories import user_repository
from app.core.database import get_db
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization

router = APIRouter(tags=["users"])

@router.get("/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    """
    Get a specific user's profile by ID.
    """
    db_user = db.query(User).options(joinedload(User.organization)).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization check
    if isinstance(current_user, Organization):
        if db_user.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    elif isinstance(current_user, User):
        if current_user.id != user_id and current_user.role != "mentor":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    user_out = UserOut.from_orm(db_user)
    return create_response(success=True, message="User retrieved successfully", data=user_out.model_dump())

@router.get("/organization/users")
def read_organization_users(db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    """
    Get all users for the authenticated organization.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Access denied")

    users = user_repository.get_users_by_organization(db, organization_id=current_user.id)
    users_out = [UserOut.from_orm(user) for user in users]
    return create_response(success=True, message="Users retrieved successfully", data=[user.model_dump() for user in users_out])

@router.put("/{user_id}", response_model=UserOut, status_code=200)
def update_profile(user_id: int, user_update: dict, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    if isinstance(current_user, User) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Can only update own profile")
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in user_update.items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return UserOut.from_orm(db_user)