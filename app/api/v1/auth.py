from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
import datetime

from app.core.database import get_db
from app.models.organization import Organization
from app.repositories import user_repository, organization_repository
from app.repositories.invitation_repository import get_invitation_by_code
from app.core.hashing import verify_password, get_password_hash
from app.core.security import (
    create_access_token,
    create_reset_token,
    get_current_user_or_organization,
    verify_reset_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
# from app.core.email_utils import send_email
from app.core.email_utils import send_password_reset_email
from app.schemas.response_model import create_response
from app.repositories.user_org_repository import link_user_to_org
# Schemas
from app.schemas.user import UserCreate, UserOut
from app.schemas.organization import OrganizationOut
from app.schemas.auth import Token, PasswordResetRequest, PasswordResetConfirm, LoginRequest

router = APIRouter()




@router.post("/register/user")
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    invitation_code: str = Query(..., description="Invitation code is required")
):
    """
    Register a new user with an invitation code.
    Links user to organization via many-to-many relationship.
    """
    # Validate invitation
    invitation = get_invitation_by_code(db, invitation_code)
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid invitation code")

    if invitation.is_used:
        raise HTTPException(status_code=400, detail="This invitation has already been used")

    if invitation.expires_at < datetime.datetime.now(datetime.timezone.utc):
        # Update status to expired before raising error
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired. Please request a new invitation.")

    # Prevent registration with organization email
    existing_org = organization_repository.get_organization_by_email(db, user.email)
    if existing_org:
        raise HTTPException(status_code=400, detail="This email is registered to an organization")

    # Check if user already exists
    existing_user = user_repository.get_user_by_email(db, user.email)

    if not existing_user:
        # === NEW USER REGISTRATION ===
        user_entity = user_repository.create_user(
            db=db,
            user=user
            # organization_id removed - not needed for many-to-many
        )

        # Flush to assign ID
        db.flush()

        # Link user to organization via many-to-many
        link_user_to_org(db, user_entity.id, invitation.organization_id)

    else:
        # === EXISTING USER - ADD TO NEW ORGANIZATION ===
        user_entity = existing_user

        # Check if already linked to this organization
        user_orgs = {org.id for org in user_entity.organizations}

        if invitation.organization_id in user_orgs:
            raise HTTPException(
                status_code=400,
                detail="You are already a member of this organization"
            )

        link_user_to_org(db, user_entity.id, invitation.organization_id)

    # ⚠️ UPDATED: Properly mark invitation as accepted
    invitation.is_used = True
    invitation.accepted = True
    invitation.accepted_at = datetime.datetime.now(datetime.timezone.utc)
    invitation.status = "accepted"  

    # Commit transaction
    db.commit()
    db.refresh(user_entity)

    # Get user's primary organization (first one they joined)
    primary_org = user_entity.organizations[0] if user_entity.organizations else None

    if not primary_org:
        raise HTTPException(status_code=500, detail="User has no organization")

    organization_out = OrganizationOut.model_validate(primary_org)

    # Generate token
    token = create_access_token(
        data={"sub": user_entity.email},
        entity_type="user"
    )

    return create_response(
        success=True,
        message="User registration completed successfully",
        data=Token(
            access_token=token,
            token_type="bearer",
            user=UserOut.model_validate(user_entity),
            onboarding_completed=False,
            organization=organization_out,
        )
    )



# ----------------------------
# LOGIN
# ----------------------------
@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # Normalize email
    login_email = login_data.email.lower()

    # Try user -> then organization
    user_obj = user_repository.get_user_by_email(db, login_email)
    entity_type = "user"
    if not user_obj:
        user_obj = organization_repository.get_organization_by_email(db, login_email)
        entity_type = "organization"

    if not user_obj or not verify_password(login_data.password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Adjust expiry based on "remember me"
    expires_delta = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if login_data.remember_me:
        expires_delta = datetime.timedelta(days=7)

    access_token = create_access_token(
        data={"sub": user_obj.email},
        expires_delta=expires_delta,
        entity_type=entity_type
    )

    # Distinguish between organization and user
    if entity_type == "organization":  # Organization
        return create_response(
            success=True,
            message="Organization login successful",
            data=Token(access_token=access_token, token_type="bearer",
                       organization=OrganizationOut.model_validate(user_obj))
        )
    else:  # User
        return create_response(
            success=True,
            message="User login successful",
            data=Token(access_token=access_token, token_type="bearer",
                       user=UserOut.model_validate(user_obj))
        )


# ----------------------------
# PASSWORD RESET REQUEST
# ----------------------------
@router.post("/password-reset")
async def request_password_reset(request: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = request.email.lower()
    user_obj = user_repository.get_user_by_email(db, email) or \
               organization_repository.get_organization_by_email(db, email)

    # Always send same message for privacy
    if not user_obj:
        return create_response(success=True, message="If the email exists, a reset link has been sent")

    token = create_reset_token(email)
    reset_link = f"https://team-iq-frontend.vercel.app/reset-password?token={token}"

    background_tasks.add_task(send_password_reset_email, email, reset_link)


    return create_response(
        success=True,
        message="Reset email sent",
        # data={"reset_link": reset_link}
    )



# ----------------------------
# PASSWORD RESET CONFIRM
# ----------------------------
@router.post("/password-reset/confirm")
def confirm_password_reset(confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Confirm the password reset using a valid token."""
    email = verify_reset_token(confirm.token)

    user_obj = user_repository.get_user_by_email(db, email) or \
               organization_repository.get_organization_by_email(db, email)

    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        hashed_pw = get_password_hash(confirm.new_password)
        user_obj.hashed_password = hashed_pw
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the password. Please try again."
        )

    return create_response(success=True, message="Password reset successful")



@router.post("/logout")
def logout(
    current_user = Depends(get_current_user_or_organization)
):
    """
    Logout endpoint

    In token-based auth, logout is handled client-side by:
    1. Removing token from localStorage/cookies
    2. Optional: Add token to blacklist (implement if needed)

    This endpoint can be used to log the logout event
    """
    from datetime import datetime

    user_type = "organization" if isinstance(current_user, Organization) else "user"
    user_id = current_user.id

    # Log logout event (optional)
    print(f"[LOGOUT] {user_type.upper()} ID {user_id} logged out at {datetime.utcnow()}")

    return create_response(
        success=True,
        message="Logged out successfully. Please remove token from client.",
        data={
            "user_type": user_type,
            "user_id": user_id,
            "logged_out_at": datetime.utcnow().isoformat()
        }
    )
