from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.organization import (
    OrganizationSignUp,
    OrganizationOut,
    OrganizationUpdate,
    OrganizationOnboardingComplete
)
from app.repositories import organization_repository, user_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization, create_access_token
from app.models.organization import Organization, UserRole
from app.core.hashing import get_password_hash
from app.core.email_utils import send_organization_signup_email, send_onboarding_complete_email
from app.schemas.auth import Token

router = APIRouter()


# ============================================================================
# ORGANIZATION SIGNUP (Step 1: Basic Registration)
# ============================================================================

@router.post("/signup", status_code=201)
async def signup(
    org: OrganizationSignUp,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Step 1: Organization Signup
    Creates organization with minimal required fields
    """
    # Global email validation
    existing_org = organization_repository.get_organization_by_email(db, org.email)
    existing_user = user_repository.get_user_by_email(db, org.email)
    if existing_org or existing_user:
        raise HTTPException(status_code=400, detail="Email already registered in the system")

    # Check for duplicate organization name
    if organization_repository.get_organization_by_name(db, org.organization_name):
        raise HTTPException(status_code=400, detail="Organization name already exists")

    # Create organization with minimal fields
    hashed_password = get_password_hash(org.password)

    new_org = organization_repository.create_organization(
        db=db,
        org_data={
            "organization_name": org.organization_name,
            "team_size": org.team_size,
            "email": org.email,
            "country": org.country,
            "hashed_password": hashed_password,
            "role": UserRole.ORGANIZATION
        }
    )

    db.commit()
    db.refresh(new_org)

    # Issue organization token
    access_token = create_access_token(
        data={"sub": new_org.email},
        entity_type="organization"
    )

    # Send signup email asynchronously
    background_tasks.add_task(
        send_organization_signup_email,
        new_org.email,
        new_org.organization_name
    )

    # Return token and org info
    org_out = OrganizationOut.model_validate(new_org)
    token_response = Token(
        access_token=access_token,
        token_type="bearer",
        organization=org_out
    )

    return create_response(
        success=True,
        message="Organization signup successful. Please complete your profile to enable integrations.",
        data=token_response
    )


# ============================================================================
# ONBOARDING COMPLETE (Step 2: KYC/Profile Completion)
# ============================================================================
@router.patch("/onboarding-complete", status_code=200)
async def onboarding_complete(
    org_data: OrganizationOnboardingComplete,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Complete organization onboarding (KYC)
    Requires domain_link for integrations
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can complete onboarding")

    db_org = organization_repository.get_organization_by_id(db, current_user.id)
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Update with validated data
    update_data = org_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)

    db.commit()
    db.refresh(db_org)

    # Send confirmation
    background_tasks.add_task(
        send_onboarding_complete_email,
        db_org.email,
        db_org.organization_name
    )

    return create_response(
        success=True,
        message="Organization onboarding completed! You can now create projects with integrations.",
        data=OrganizationOut.model_validate(db_org)
    )


# ============================================================================
# UPDATE ORGANIZATION PROFILE (Anytime after onboarding)
# ============================================================================

@router.patch("/{org_id}", status_code=200)
def update_organization(
    org_id: int,
    org_update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Update organization profile (can be used anytime after signup)
    Partial updates - only send fields you want to change
    """
    # Authorization check
    if not isinstance(current_user, Organization) or current_user.id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db_org = organization_repository.get_organization_by_id(db, org_id)
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Apply partial updates
    update_data = org_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)

    db.commit()
    db.refresh(db_org)

    return create_response(
        success=True,
        message="Organization updated successfully",
        data=OrganizationOut.model_validate(db_org)
    )


# ============================================================================
# GET ORGANIZATION PROFILE
# ============================================================================

# @router.get("/{org_id}", status_code=200)
# def get_organization(
#     org_id: int,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """Get organization profile details"""
#     # Authorization check
#     if not isinstance(current_user, Organization) or current_user.id != org_id:
#         raise HTTPException(status_code=403, detail="Access denied")

#     db_org = organization_repository.get_organization_by_id(db, org_id)
#     if not db_org:
#         raise HTTPException(status_code=404, detail="Organization not found")

#     return create_response(
#         success=True,
#         message="Organization retrieved successfully",
#         data=OrganizationOut.model_validate(db_org)
#     )


# ============================================================================
# GET CURRENT ORGANIZATION PROFILE
# ============================================================================

@router.get("/me/profile", status_code=200)
def get_my_organization_profile(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Get current authenticated organization's profile"""
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can access this endpoint")

    return create_response(
        success=True,
        message="Organization profile retrieved successfully",
        data=OrganizationOut.model_validate(current_user)
    )
