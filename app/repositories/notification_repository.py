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
