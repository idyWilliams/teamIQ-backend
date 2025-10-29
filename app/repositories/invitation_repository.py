from sqlalchemy.orm import Session
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate
from app.models.user import User
from app.models.user_organizations import UserOrganization
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.core.logger import logger
import uuid


def create_invitation(db: Session, invitation: InvitationCreate, organization_id: int) -> Invitation:
    """Creates a new invitation that expires in 48 hours"""
    invitation_code = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=48)

    db_invitation = Invitation(
        **invitation.model_dump(),
        invitation_code=invitation_code,
        organization_id=organization_id,
        expires_at=expires_at,
        is_used=False
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)

    logger.info(
        f"📨 New Invitation Created — Email: {db_invitation.email}, "
        f"OrgID: {organization_id}, Code: {db_invitation.invitation_code}, "
        f"ExpiresAt: {db_invitation.expires_at.isoformat()}"
    )
    return db_invitation


def get_invitation_by_code(db: Session, invitation_code: str):
    """Fetch an invitation by its unique code"""
    return db.query(Invitation).filter(Invitation.invitation_code == invitation_code).first()


def get_active_invite_by_email_and_org(db: Session, email: str, organization_id: int):
    """
    Prevents sending duplicate active invitations.
    Finds an invitation by email and org that’s still valid (not expired and not used).
    """
    return (
        db.query(Invitation)
        .filter(
            Invitation.email == email.lower(),
            Invitation.organization_id == organization_id,
            Invitation.is_used == False,
            Invitation.expires_at > datetime.utcnow()
        )
        .first()
    )


def accept_invitation(db: Session, invitation_code: str, user_id: int):
    """Marks an invitation as accepted and attaches user to organization"""
    invitation = get_invitation_by_code(db, invitation_code)
    if not invitation or invitation.is_used or invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")

    # Mark invitation as used
    invitation.is_used = True

    # Link user to organization
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.organization_id = invitation.organization_id

    db.commit()
    return invitation


# def link_user_to_org(db: Session, user_id: int, org_id: int):
#     """Links an existing user to an organization in the user_organizations table if not already added"""
#     existing = (
#         db.query(UserOrganization)
#         .filter(
#             UserOrganization.user_id == user_id,
#             UserOrganization.organization_id == org_id
#         )
#         .first()
#     )
#     if not existing:
#         db.add(UserOrganization(user_id=user_id, organization_id=org_id))
#         db.commit()


def link_user_to_org(db: Session, user_id: int, org_id: int):
    """
    Link a user to an organization via the user_organizations junction table.

    Args:
        db: Database session
        user_id: The user's ID (must not be None - user must be flushed first)
        org_id: The organization's ID

    Note: Does not commit - caller must handle transaction
    """
    # Defensive check
    if user_id is None:
        raise ValueError("user_id cannot be None. User must be flushed before linking to organization.")
    if org_id is None:
        raise ValueError("org_id cannot be None.")

    # Check if link already exists
    existing = (
        db.query(UserOrganization)
        .filter(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id
        )
        .first()
    )

    # Only create if link doesn't exist
    if not existing:
        user_org = UserOrganization(
            user_id=user_id,
            organization_id=org_id
        )
        db.add(user_org)
        # Don't commit - let the caller manage the transaction