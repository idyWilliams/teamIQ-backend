
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationOut
from app.repositories import invitation_repository, user_repository
from app.core.security import get_current_user_or_organization
from app.models.organization import Organization
from app.core.email_utils import send_invitation_email
from app.schemas.user import UserCreate, UserOut
import datetime
from app.schemas.response_model import create_response

router = APIRouter(prefix="/invitations", tags=["invitations"])

@router.post("/")
def create_invitation(
    invitation: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: Organization = Depends(get_current_user_or_organization),
):
    """
    Create and send an invitation to a new user.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create an invitation.",
        )

    db_invitation = invitation_repository.create_invitation(
        db=db, invitation=invitation, organization_id=current_user.id
    )

    # Send invitation email
    send_invitation_email(
        email_to=db_invitation.email,
        invitation_code=db_invitation.invitation_code,
    )
    invitation_out = InvitationOut.from_orm(db_invitation)
    invitation_out.createdAt = db_invitation.createdAt
    return create_response(success=True, message="Invitation sent successfully", data=invitation_out.model_dump())

@router.post("/accept")
def accept_invitation(
    invitation_code: str,
    user_create: UserCreate,
    db: Session = Depends(get_db),
):
    """
    Accept an invitation and create a new user account.
    """
    invitation = invitation_repository.get_invitation_by_code(db, invitation_code)
    if not invitation or invitation.accepted or invitation.expires_at < datetime.datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation code.",
        )

    user = user_repository.create_user(db, user_create, organization_id=invitation.organization_id)
    
    invitation.accepted = True
    db.commit()

    return create_response(success=True, message="User created successfully", data=UserOut.from_orm(user).model_dump())
