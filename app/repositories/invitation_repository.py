

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.invitation import Invitation
from app.repositories.user_org_repository import link_user_to_org
from app.schemas.invitation import InvitationCreate
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.core.logger import logger
import uuid


def create_invitation(db: Session, invitation: InvitationCreate, organization_id: int) -> Invitation:
    """Creates a new invitation that expires in 48 hours"""
    invitation_code = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=48)

    db_invitation = Invitation(
        email=invitation.email.lower().strip(),
        role=invitation.role,
        track=invitation.track,
        invitation_code=invitation_code,
        organization_id=organization_id,
        expires_at=expires_at,
        is_used=False,
        status="pending"
    )

    try:
        db.add(db_invitation)
        db.commit()
        db.refresh(db_invitation)

        logger.info(
            f"📨 New Invitation Created — Email: {db_invitation.email}, "
            f"OrgID: {organization_id}, Code: {db_invitation.invitation_code}, "
            f"ExpiresAt: {db_invitation.expires_at.isoformat()}"
        )
        return db_invitation

    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()

        logger.error(f"IntegrityError creating invitation: {error_msg}")

        # Check if it's the duplicate email+org constraint
        if "uq_invitation_email_org" in error_msg or "duplicate key" in error_msg:
            if "email" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"An invitation for {invitation.email} already exists in your organization. Please revoke or resend the existing invitation instead."
                )

        # Generic constraint error
        raise HTTPException(
            status_code=400,
            detail="Unable to create invitation. This email may already have a pending invitation."
        )


def get_invitation_by_code(db: Session, invitation_code: str):
    """Fetch an invitation by its unique code"""
    return db.query(Invitation).filter(Invitation.invitation_code == invitation_code).first()


def get_invitation_by_id(db: Session, invitation_id: int):
    """Fetch an invitation by its primary key ID"""
    return db.query(Invitation).filter(Invitation.id == invitation_id).first()


def get_all_invitations_for_organization(db: Session, organization_id: int):
    """Fetch all invitations for an organization and update their statuses"""
    invitations = db.query(Invitation).filter(Invitation.organization_id == organization_id).all()

    # Update statuses based on current state
    for inv in invitations:
        inv.compute_status()

    db.commit()
    return invitations


def get_active_invite_by_email_and_org(db: Session, email: str, organization_id: int):
    """
    Prevents sending duplicate active invitations.
    Finds an invitation by email and org that's still valid (not expired and not used).
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

    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid invitation code")

    if invitation.is_used:
        raise HTTPException(
            status_code=400,
            detail="This invitation has already been used"
        )

    if invitation.expires_at < datetime.utcnow():
        # Update status to expired
        invitation.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="This invitation has expired. Please request a new invitation."
        )

    # Mark invitation as used and accepted
    invitation.is_used = True
    invitation.accepted = True
    invitation.accepted_at = datetime.utcnow()
    invitation.status = "accepted"

    # Link user to organization
    link_user_to_org(db, user_id, invitation.organization_id)

    db.commit()

    logger.info(
        f"✅ Invitation accepted — Email: {invitation.email}, "
        f"UserID: {user_id}, OrgID: {invitation.organization_id}"
    )

    return invitation
