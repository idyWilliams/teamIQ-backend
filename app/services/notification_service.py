import logging
import os
import asyncio
from typing import Optional

from sqlalchemy.orm import Session
from app.repositories.notification_repository import create_notification, get_notifications, mark_read
from app.schemas.notification import NotificationCreate
from app.models.user import User  # optional, used only if you want to look up user details
from app.core.websocket_manager import manager

# keep logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment loading (if you use dotenv in your app; keep it but load early)
from dotenv import load_dotenv
load_dotenv()

# NOTE: email/slack pieces have been intentionally removed from the primary flow.
# The pattern now is: create DB notification and broadcast to connected WebSocket clients.

async def trigger_notification(db: Session, user_or_org_key: str, title: str, message: str, type: str = "info"):
    """
    Create a notification in DB and broadcast it to the connected client identified by user_or_org_key.
    user_or_org_key should be in the format "user:<id>" or "org:<id>".
    """
    try:
        # prepare notification create schema
        # Extract numeric ids so we save to DB properly:
        user_id = None
        org_id = None
        if user_or_org_key.startswith("user:"):
            try:
                user_id = int(user_or_org_key.split(":", 1)[1])
            except Exception:
                user_id = None
        elif user_or_org_key.startswith("org:"):
            try:
                org_id = int(user_or_org_key.split(":", 1)[1])
            except Exception:
                org_id = None

        notif_in = NotificationCreate(title=title, message=message, type=type)
        db_notif = create_notification(db, notif_in, user_id=user_id, org_id=org_id)

        # payload to send over websockets
        payload = {
            "type": "notification",
            "data": {
                "id": db_notif.id,
                "title": db_notif.title,
                "message": db_notif.message,
                "is_read": db_notif.is_read,
                "type": db_notif.type,
                "createdAt": db_notif.createdAt.isoformat() if db_notif.createdAt else None,
            },
        }

        # Send to connection if present
        await manager.send_personal_message(user_or_org_key, payload)
        logger.info(f"Notification created and sent to {user_or_org_key}: {title}")
        return db_notif
    except Exception as e:
        logger.error(f"Error creating/sending notification: {e}")
        return None

def trigger_notification_sync(db: Session, user_or_org_key: str, title: str, message: str, type: str = "info"):
    """
    Sync wrapper you can call from synchronous code paths; schedules the async notification.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # No running event loop (e.g., in certain thread contexts). Create a new one.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # We schedule the async coroutine
    return loop.create_task(trigger_notification(db, user_or_org_key, title, message, type))

# Utility functions to fetch or mark notifications via repository if you still need them
def fetch_notifications_for_user(db: Session, user_id: int, is_read: Optional[bool] = None):
    return get_notifications(db, user_id=user_id, is_read=is_read)

def mark_notification_read(db: Session, notif_id: int):
    return mark_read(db, notif_id)
