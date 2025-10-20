from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.repositories.notification_repository import (
    get_notifications,
    mark_notification_read,
    create_notification_preference,
    get_notification_preference,
    update_notification_preference
)
from app.schemas.notification import (
    NotificationOut,
    NotificationPreferenceCreate,
    NotificationPreferenceOut
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/notifications/{user_id}", response_model=list[NotificationOut])
def get_user_notifications(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        return get_notifications(db, user_id, skip, limit)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching notifications for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")

@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(notification_id: int, db: Session = Depends(get_db)):
    try:
        return mark_notification_read(db, notification_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

@router.post("/notification-preferences", response_model=NotificationPreferenceOut)
def create_user_notification_preference(preference: NotificationPreferenceCreate, db: Session = Depends(get_db)):
    try:
        return create_notification_preference(db, preference)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating notification preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification preferences")

@router.get("/notification-preferences/{user_id}", response_model=NotificationPreferenceOut)
def get_user_notification_preference(user_id: int, db: Session = Depends(get_db)):
    try:
        return get_notification_preference(db, user_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching notification preferences for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notification preferences")

@router.put("/notification-preferences/{user_id}", response_model=NotificationPreferenceOut)
def update_user_notification_preference(user_id: int, preference: NotificationPreferenceCreate, db: Session = Depends(get_db)):
    try:
        return update_notification_preference(db, user_id, preference)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating notification preferences for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")