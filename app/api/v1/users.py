from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserOut
from app.repositories import user_repository
from app.core.database import get_db
# from app.core.security import get_current_user # Placeholder for auth dependency

router = APIRouter(prefix="/users", tags=["users"])


# @router.get("/me", response_model=UserOut)
# def read_users_me(current_user: UserOut = Depends(get_current_user)):
#     """
#     Get the current authenticated user's profile.
#     """
#     return current_user


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific user's profile by ID.
    """
    # This function needs to be added to the repository
    db_user = db.query(user_repository.User).filter(user_repository.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user