from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import datetime

from app.core.database import get_db
from app.repositories import user_repository, organization_repository
from app.repositories.invitation_repository import get_invitation_by_code, accept_invitation
from app.core.hashing import verify_password, get_password_hash
from app.core.security import (
    create_access_token,
    create_reset_token,
    verify_reset_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
# from app.core.email_utils import send_email
from app.core.email_utils import send_password_reset_email
from app.schemas.response_model import create_response
from app.repositories.user_org_repository import link_user_to_org
# Schemas
from app.schemas.user import UserCreate, UserOut
from app.schemas.organization import OrganizationSignUp, OrganizationOut
from app.schemas.auth import Token, PasswordResetRequest, PasswordResetConfirm, LoginRequest

router = APIRouter()


# ----------------------------
# USER REGISTRATION
# ----------------------------


# @router.post("/register/user")
# def register_user(
#     user: UserCreate,
#     db: Session = Depends(get_db),
#     invitation_code: str = Query(..., description="Invitation code is required for user registration")
# ):
#     invitation = get_invitation_by_code(db, invitation_code)
#     if not invitation or invitation.is_used or invitation.expires_at < datetime.datetime.now(datetime.timezone.utc):
#         raise HTTPException(status_code=400, detail="Invalid or expired invitation code")

#     # Cannot register with an organization email
#     existing_org = organization_repository.get_organization_by_email(db, user.email)
#     if existing_org:
#         raise HTTPException(status_code=400, detail="This email is registered to an organization")

#     # Proceed
#     existing_user = user_repository.get_user_by_email(db, user.email)
#     if not existing_user:
#         # Create a new user
#         user_entity = user_repository.create_user(db, user)
#         user_entity.organization_id = invitation.organization_id
#         db.flush() # Assign an ID to the new user before linking
#         link_user_to_org(db, user_entity.id, invitation.organization_id)
#     else:
#         # If user exists, check if they are already in the organization
#         user_entity = existing_user
#         user_orgs = {org.id for org in user_entity.organizations}
#         if invitation.organization_id not in user_orgs:
#             link_user_to_org(db, user_entity.id, invitation.organization_id)

#     invitation.is_used = True
#     db.commit()
#     db.refresh(user_entity)

#     token = create_access_token(data={"sub": user_entity.email})
#     return create_response(
#         success=True,
#         message="User registration completed successfully",
#         data=Token(
#             access_token=token,
#             token_type="bearer",
#             user=UserOut.model_validate(user_entity)
#         )
#     )

@router.post("/register/user")
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    invitation_code: str = Query(..., description="Invitation code is required for user registration")
):
    """
    Register a new user with an invitation code.
    If user already exists, adds them to the invited organization.
    """
    # Validate invitation code
    invitation = get_invitation_by_code(db, invitation_code)
    if not invitation or invitation.is_used or invitation.expires_at < datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired invitation code")

    # Prevent registration with organization email
    existing_org = organization_repository.get_organization_by_email(db, user.email)
    if existing_org:
        raise HTTPException(status_code=400, detail="This email is registered to an organization")

    # Check if user already exists
    existing_user = user_repository.get_user_by_email(db, user.email)

    if not existing_user:
        # === NEW USER REGISTRATION ===

        # Create user (not committed yet)
        user_entity = user_repository.create_user(
            db=db,
            user=user,
            organization_id=invitation.organization_id
        )

        # Flush to assign ID to user_entity before using it in foreign key
        db.flush()

        # Now user_entity.id is available - link to organization
        link_user_to_org(db, user_entity.id, invitation.organization_id)

    else:
        # === EXISTING USER - ADD TO NEW ORGANIZATION ===

        user_entity = existing_user

        # Update primary organization if not set
        if not user_entity.organization_id:
            user_entity.organization_id = invitation.organization_id

        # Check if already linked to this organization
        user_orgs = {org.id for org in user_entity.organizations}

        if invitation.organization_id not in user_orgs:
            # Link existing user to the new organization
            # user_entity.id already exists, no need to flush
            link_user_to_org(db, user_entity.id, invitation.organization_id)

    # Mark invitation as used
    invitation.is_used = True

    # Commit all changes as a single transaction
    db.commit()

    # Refresh to load all relationships and updated fields
    db.refresh(user_entity)

    # Fetch organization details
    organization = organization_repository.get_organization_by_id(db, user_entity.organization_id)
    organization_out = OrganizationOut.model_validate(organization)

    # Generate access token
    token = create_access_token(data={"sub": user_entity.email}, entity_type="user")

    return create_response(
        success=True,
        message="User registration completed successfully",
        data=Token(
            access_token=token,
            token_type="bearer",
            user=UserOut.model_validate(user_entity),
            organization=organization_out
        )
    )


# ----------------------------
# ORGANIZATION REGISTRATION
# ----------------------------
# @router.post("/register/organization")
# def register_organization(org: OrganizationSignUp, db: Session = Depends(get_db)):
#     if organization_repository.get_organization_by_name(db, org.organization_name):
#         raise HTTPException(status_code=400, detail="Organization name already registered")

#     if organization_repository.get_organization_by_email(db, org.email):
#         raise HTTPException(status_code=400, detail="Email already registered")

#     hashed_password = get_password_hash(org.password)

#     new_org = organization_repository.create_organization(
#         db=db,
#         org_data={
#             "organization_name": org.organization_name,
#             "team_size": org.team_size,
#             "email": org.email,
#             "country": org.country,
#             "hashed_password": hashed_password,
#             "role": "organization"
#         }
#     )
#     db.commit()
#     db.refresh(new_org)

#     access_token = create_access_token(data={"sub": new_org.email})
#     org_out = OrganizationOut.model_validate(new_org)

#     return create_response(
#         success=True,
#         message="Organization registered successfully",
#         data=Token(
#             access_token=access_token,
#             token_type="bearer",
#             organization=org_out
#         )
#     )


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
async def request_password_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    email = request.email.lower()
    user_obj = user_repository.get_user_by_email(db, email) or \
               organization_repository.get_organization_by_email(db, email)

    # Always send same message for privacy
    if not user_obj:
        return create_response(success=True, message="If the email exists, a reset link has been sent")

    token = create_reset_token(email)
    reset_link = f"https://team-iq-frontend.vercel.app/reset?token={token}"

    await send_password_reset_email(email, reset_link)

    return create_response(success=True, message="Reset email sent")



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

    hashed_pw = get_password_hash(confirm.new_password)
    user_obj.hashed_password = hashed_pw
    db.commit()

    return create_response(success=True, message="Password reset successful")
