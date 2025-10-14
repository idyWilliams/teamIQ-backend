from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationOut
from app.repositories import invitation_repository
from app.core.email_utils import send_invitation_email
from app.core.security import get_current_user_or_organization
from app.schemas.response_model import create_response
from app.models.organization import Organization

router = APIRouter(prefix="/invitations", tags=["invitations"])

@router.post("/", response_model=InvitationOut)
async def create_invitation(invitation: InvitationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can invite")
    db_inv = invitation_repository.create_invitation(db, invitation, current_user.id)
    await send_invitation_email(invitation.email, db_inv.invitation_code)
    return create_response(success=True, data=InvitationOut.from_orm(db_inv))