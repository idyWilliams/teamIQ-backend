from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_or_organization
from app.models.user import User
from datetime import datetime, timezone

def get_current_user_and_update_last_seen(
    current_user: User = Depends(get_current_user_or_organization),
    db: Session = Depends(get_db)
):
    if isinstance(current_user, User):
        current_user.last_seen = datetime.now(timezone.utc)
        db.commit()
    return current_user
