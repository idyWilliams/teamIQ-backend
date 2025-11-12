from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.invitation import InvitationCreate, InvitationOut, InvitationOutWithStatus
from app.repositories import invitation_repository, user_repository, organization_repository
from app.core.email_utils import send_invitation_email
from app.core.security import get_current_user_or_organization
from app.schemas.response_model import create_response, APIResponse
from app.models.organization import Organization
import logging

router = APIRouter()
logger = logging.getLogger("invitations")

@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitation: InvitationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Allows an organization to invite users while enforcing global email uniqueness"""
    if not isinstance(current_user, Organization):
        user_type = type(current_user).__name__
        raise HTTPException(
            status_code=403,
            detail=f"Only organizations can send invitations, but you are authenticated as a '{user_type}'. Please log in as an organization."
        )

    # Check if email is used by an organization — orgs cannot be invited
    existing_org = organization_repository.get_organization_by_email(db, invitation.email)
    if existing_org:
        raise HTTPException(status_code=400, detail="Organizations cannot be invited")

    # Check if email is already tied to a user
    existing_user = user_repository.get_user_by_email(db, invitation.email)

    # If user exists but not yet linked to this org, valid — if linked already, block
    if existing_user:
        user_org_ids = {org.id for org in existing_user.organizations}
        if current_user.id in user_org_ids:
            raise HTTPException(status_code=400, detail="This user already belongs to your organization")

    # Prevent duplicate active invitations
    existing_invite = invitation_repository.get_active_invite_by_email_and_org(db, invitation.email, current_user.id)
    if existing_invite:
        raise HTTPException(status_code=400, detail="An active invitation already exists for this email")

    # Create new invitation (48-hour expiry)
    db_inv = invitation_repository.create_invitation(db, invitation, current_user.id)


    invite_link = f"https://team-iq-frontend.vercel.app/signup?invitation_code={db_inv.invitation_code}&email={invitation.email}"
    background_tasks.add_task(send_invitation_email, invitation.email, invite_link)

    logger.info(f"Invitation email sent to {invitation.email} (OrgID={current_user.id}) link: {invite_link}")

    invitation_out = InvitationOut.model_validate(db_inv)
    invitation_out.invite_link = invite_link

    return create_response(
        success=True,
        message=f"Invitation sent to {invitation.email}",
        # data=invitation_out
    )

@router.get("/", response_model=APIResponse, status_code=status.HTTP_200_OK)
def get_all_invitations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all invitations for the organization.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can view invitations")

    invitations = invitation_repository.get_all_invitations_for_organization(db, current_user.id)

    # Use the new schema with status
    invitations_out = [InvitationOutWithStatus.model_validate(inv) for inv in invitations]

    return create_response(
        success=True,
        message="Invitations retrieved successfully",
        data=invitations_out
    )
