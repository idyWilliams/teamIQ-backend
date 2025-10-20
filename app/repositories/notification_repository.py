<<<<<<< HEAD
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.notification import Notification, NotificationPreference, NotificationType
from app.schemas.notification import NotificationCreate, NotificationPreferenceCreate
from app.models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_notification(db: Session, notification: NotificationCreate):
    try:
        db_notification = Notification(**notification.dict())
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        logger.info(f"Created notification for user {notification.user_id}: {notification.type}")
        return db_notification
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

def get_notifications(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    try:
        return db.query(Notification).filter(Notification.user_id == user_id).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Error fetching notifications for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")

def mark_notification_read(db: Session, notification_id: int):
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        notification.is_read = True
        db.commit()
        return notification
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to mark notification as read")

def create_notification_preference(db: Session, preference: NotificationPreferenceCreate):
    try:
        db_preference = NotificationPreference(**preference.dict())
        db.add(db_preference)
        db.commit()
        db.refresh(db_preference)
        logger.info(f"Created notification preferences for user {preference.user_id}")
        return db_preference
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating notification preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create notification preferences")

def get_notification_preference(db: Session, user_id: int):
    try:
        preference = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
        if not preference:
            raise HTTPException(status_code=404, detail="Notification preferences not found")
        return preference
    except Exception as e:
        logger.error(f"Error fetching notification preferences for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch notification preferences")

def update_notification_preference(db: Session, user_id: int, preference: NotificationPreferenceCreate):
    try:
        db_preference = db.query(NotificationPreference).filter(NotificationPreference.user_id == user_id).first()
        if not db_preference:
            raise HTTPException(status_code=404, detail="Notification preferences not found")
        for key, value in preference.dict(exclude={"user_id"}).items():
            setattr(db_preference, key, value)
        db.commit()
        db.refresh(db_preference)
        logger.info(f"Updated notification preferences for user {user_id}")
        return db_preference
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating notification preferences: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update notification preferences")
=======
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate

def create_notification(db: Session, notif: NotificationCreate, user_id: int = None, org_id: int = None):
    db_notif = Notification(**notif.model_dump(), user_id=user_id, organization_id=org_id)
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif

def get_notifications(db: Session, user_id: int = None, org_id: int = None, is_read: bool = None):
    query = db.query(Notification)
    if user_id:
        query = query.filter(Notification.user_id == user_id)
    if org_id:
        query = query.filter(Notification.organization_id == org_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    return query.order_by(Notification.createdAt.desc()).all()

def mark_read(db: Session, notif_id: int):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if notif:
        notif.is_read = True
        db.commit()
    return notif
>>>>>>> origin/staging
