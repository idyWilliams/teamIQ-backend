
from sqlalchemy.orm import Session
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate
import uuid

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
