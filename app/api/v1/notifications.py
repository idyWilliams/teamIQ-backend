from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.notification import NotificationCreate, NotificationOut
from app.repositories import notification_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from typing import List

router = APIRouter()

@router.post("/", response_model=NotificationOut)
def create_notification(notif: NotificationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    db_notif = notification_repository.create_notification(db, notif, user_id=user_id, org_id=org_id)
    return create_response(success=True, data=NotificationOut.from_orm(db_notif))

@router.get("/", response_model=List[NotificationOut])
def get_notifications(is_read: bool = None, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    notifs = notification_repository.get_notifications(db, user_id=user_id, org_id=org_id, is_read=is_read)
    return create_response(success=True, data=[NotificationOut.from_orm(n) for n in notifs])

@router.patch("/{notif_id}/read")
def mark_as_read(notif_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    notif = notification_repository.mark_read(db, notif_id)
    return create_response(success=True, data=NotificationOut.from_orm(notif) if notif else None)