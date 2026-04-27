# api/v1/invitation.py

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
from datetime import datetime, timedelta
import uuid


router = APIRouter()
logger = logging.getLogger("invitations")


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invitation: InvitationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Allows an organization to invite users.
    Email must be unique per organization (can invite same email to different orgs).
    """
    if not isinstance(current_user, Organization):
        user_type = type(current_user).__name__
        raise HTTPException(
            status_code=403,
            detail=f"Only organizations can send invitations, but you are authenticated as a '{user_type}'. Please log in as an organization."
        )

    # Normalize email to lowercase and strip whitespace
    normalized_email = invitation.email.lower().strip()

    # Check if email is used by an organization — orgs cannot be invited
    existing_org = organization_repository.get_organization_by_email(db, normalized_email)
    if existing_org:
        raise HTTPException(
            status_code=400,
            detail="This email belongs to an organization account and cannot be invited as a user."
        )

    # Check if email is already tied to a user
    existing_user = user_repository.get_user_by_email(db, normalized_email)

    # If user exists but not yet linked to this org, valid — if linked already, block
    if existing_user:
        user_org_ids = {org.id for org in existing_user.organizations}
        if current_user.id in user_org_ids:
            raise HTTPException(
                status_code=400,
                detail="This user is already a member of your organization."
            )

    # Prevent duplicate active invitations for same email in same org
    existing_invite = invitation_repository.get_active_invite_by_email_and_org(
        db, normalized_email, current_user.id
    )
    if existing_invite:
        raise HTTPException(
            status_code=400,
            detail=f"An active invitation already exists for {normalized_email}. Please revoke or resend the existing invitation instead."
        )

    try:
        # Create new invitation (48-hour expiry)
        # Error handling is now in the repository
        db_inv = invitation_repository.create_invitation(db, invitation, current_user.id)
    except HTTPException:
        raise  # Re-raise HTTPExceptions from repository
    except Exception as e:
        logger.error(f"Unexpected error creating invitation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the invitation. Please try again."
        )

    # Generate invitation link
    invite_link = f"https://team-iq-frontend.vercel.app/signup?invitation_code={db_inv.invitation_code}&email={normalized_email}"
    background_tasks.add_task(send_invitation_email, normalized_email, invite_link)

    logger.info(
        f"📨 Invitation email sent to {normalized_email} (OrgID={current_user.id}) "
        f"link: {invite_link}"
    )

    invitation_out = InvitationOut.model_validate(db_inv)
    invitation_out.invite_link = invite_link

    return create_response(
        success=True,
        message=f"Invitation successfully sent to {normalized_email}",
        # data=invitation_out
    )


@router.get("/", response_model=APIResponse, status_code=status.HTTP_200_OK)
def get_all_invitations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all invitations for the organization with their current status.
    Status is computed based on accepted/expired state.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can view invitations"
        )

    invitations = invitation_repository.get_all_invitations_for_organization(
        db, current_user.id
    )

    # Use the schema with status field
    invitations_out = [InvitationOutWithStatus.model_validate(inv) for inv in invitations]

    return create_response(
        success=True,
        message="Invitations retrieved successfully",
        data=invitations_out
    )


@router.post("/{invitation_id}/revoke", response_model=APIResponse, status_code=status.HTTP_200_OK)
def revoke_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Revoke a pending invitation.
    Revoked invitations cannot be used or resent.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can revoke invitations"
        )

    invitation = invitation_repository.get_invitation_by_id(db, invitation_id)

    if not invitation or invitation.organization_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found or you do not have permission to revoke it"
        )

    if invitation.is_used and invitation.accepted:
        raise HTTPException(
            status_code=400,
            detail="This invitation has already been accepted and cannot be revoked."
        )

    if invitation.status == "revoked":
        raise HTTPException(
            status_code=400,
            detail="This invitation has already been revoked."
        )

    # Mark as revoked
    invitation.is_used = True
    invitation.status = "revoked"
    db.commit()

    logger.info(
        f"🚫 Invitation revoked for {invitation.email} "
        f"(InvitationID={invitation_id}, OrgID={current_user.id})"
    )

    return create_response(
        success=True,
        message=f"Invitation for {invitation.email} has been successfully revoked."
    )


@router.post("/{invitation_id}/resend", response_model=APIResponse, status_code=status.HTTP_200_OK)
def resend_invitation(
    invitation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Resend an invitation that has not been accepted yet.
    Generates a new invitation code and extends expiry to 48 hours from now.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can resend invitations"
        )

    invitation = invitation_repository.get_invitation_by_id(db, invitation_id)

    if not invitation or invitation.organization_id != current_user.id:
        raise HTTPException(
            status_code=404,
            detail="Invitation not found or you do not have permission to resend it"
        )

    if invitation.is_used and invitation.accepted:
        raise HTTPException(
            status_code=400,
            detail="This invitation has already been accepted and cannot be resent."
        )

    if invitation.status == "revoked":
        raise HTTPException(
            status_code=400,
            detail="This invitation has been revoked. Please create a new invitation instead."
        )

    # Generate a new code and expiry date
    invitation.invitation_code = str(uuid.uuid4())
    invitation.expires_at = datetime.utcnow() + timedelta(hours=48)
    invitation.status = "pending"  # Reset status in case it was expired
    invitation.is_used = False  # Reset in case it was marked as used
    db.commit()
    db.refresh(invitation)

    # Resend the email with new code
    invite_link = f"https://team-iq-frontend.vercel.app/signup?invitation_code={invitation.invitation_code}&email={invitation.email}"
    background_tasks.add_task(send_invitation_email, invitation.email, invite_link)

    logger.info(
        f"📧 Invitation resent to {invitation.email} "
        f"(InvitationID={invitation_id}, OrgID={current_user.id})"
    )

    return create_response(
        success=True,
        message=f"Invitation successfully resent to {invitation.email}."
    )
