from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_or_organization
from app.models.user import User
from datetime import datetime, timezone


def get_current_user_and_update_last_seen(
    current_user = Depends(get_current_user_or_organization),
    db: Session = Depends(get_db)
):
    """
    Get current user/organization and update last_seen for users.
    Uses entity_type to avoid isinstance issues with circular imports.
    """

    entity_type = getattr(current_user, 'entity_type', None)

    if entity_type == "user":
        current_user.last_seen = datetime.now(timezone.utc)
        db.commit()
        db.refresh(current_user)

    return current_user
