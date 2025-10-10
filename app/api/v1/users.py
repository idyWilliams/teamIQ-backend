from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import UserOut
from app.repositories import user_repository
from app.core.database import get_db
from app.schemas.response_model import create_response

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}")
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific user's profile by ID.
    """
    db_user = db.query(user_repository.User).filter(user_repository.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return create_response(success=True, message="User retrieved successfully", data=UserOut.from_orm(db_user).model_dump())