from sqlalchemy.orm import Session
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate
import uuid
from datetime import datetime
from fastapi import HTTPException
from app.models.user import User

def create_invitation(db: Session, invitation: InvitationCreate, organization_id: int) -> Invitation:
    invitation_code = str(uuid.uuid4())
    db_invitation = Invitation(
        **invitation.model_dump(),
        invitation_code=invitation_code,
        organization_id=organization_id
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

def get_invitation_by_code(db: Session, invitation_code: str):
    return db.query(Invitation).filter(Invitation.invitation_code == invitation_code).first()

def accept_invitation(db: Session, invitation_code: str, user_id: int):
    invitation = get_invitation_by_code(db, invitation_code)
    if not invitation or invitation.accepted or invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    invitation.accepted = True
    # Update user org_id
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.organization_id = invitation.organization_id
    db.commit()
    return invitation