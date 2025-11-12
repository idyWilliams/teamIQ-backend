from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.user import User
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

    # Mark onboarding as complete
    db_org.onboarding_completed = True
    db_org.onboarding_completed_at = datetime.utcnow()

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


@router.delete("/members/{user_id}")
def remove_user_from_organization(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Remove a user from YOUR organization

    This will also remove them from all projects in the organization
    Only authenticated organization can remove users
    """
    from app.models.organization import Organization
    from app.models.user_organizations import UserOrganization
    from app.models.project import ProjectMember, Project

    # Authorization: Must be an authenticated organization
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can remove members"
        )

    org_id = current_user.id

    # Find membership
    membership = db.query(UserOrganization).filter(
        UserOrganization.organization_id == org_id,
        UserOrganization.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not in your organization")

    # Get user info for response
    user = db.query(User).filter(User.id == user_id).first()
    user_name = f"{user.first_name} {user.last_name}" if user else "User"

    # Remove from all organization projects
    projects_removed = db.query(ProjectMember).filter(
        ProjectMember.user_id == user_id
    ).join(Project).filter(
        Project.organization_id == org_id
    ).delete(synchronize_session=False)

    # Remove organization membership
    db.delete(membership)
    db.commit()

    return create_response(
        success=True,
        message=f"{user_name} removed from organization successfully",
        data={
            "user_id": user_id,
            "organization_id": org_id,
            "organization_name": current_user.name,
            "projects_removed_from": projects_removed
        }
    )


@router.patch("/members/{user_id}/role")
def update_user_role_in_organization(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Update a user's role in YOUR organization

    Roles: admin, manager, member
    Only authenticated organization can update roles
    """
    from app.models.user_organizations import UserOrganization

    # Authorization: Must be an authenticated organization
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can update member roles"
        )

    org_id = current_user.id

    # Validate role
    valid_roles = ["admin", "manager", "member"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    # Find membership
    membership = db.query(UserOrganization).filter(
        UserOrganization.organization_id == org_id,
        UserOrganization.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not in your organization")

    # Update role
    old_role = membership.role
    membership.role = role
    db.commit()

    user = db.query(User).filter(User.id == user_id).first()
    user_name = f"{user.first_name} {user.last_name}" if user else "User"

    return create_response(
        success=True,
        message=f"{user_name}'s role updated from {old_role} to {role}",
        data={
            "user_id": user_id,
            "user_name": user_name,
            "old_role": old_role,
            "new_role": role
        }
    )


@router.get("/members")
def get_organization_members(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all members in YOUR organization
    """
    from app.models.user_organizations import UserOrganization

    # Authorization: Must be an authenticated organization
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organizations can view members"
        )

    org_id = current_user.id

    # Get all members
    memberships = db.query(UserOrganization).filter(
        UserOrganization.organization_id == org_id
    ).all()

    members = []
    for membership in memberships:
        user = db.query(User).filter(User.id == membership.user_id).first()
        if user:
            members.append({
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat() if hasattr(membership, 'joined_at') else None,
                "profile_picture": user.profile_picture_url
            })

    return create_response(
        success=True,
        message=f"Found {len(members)} members",
        data={
            "organization_id": org_id,
            "organization_name": current_user.name,
            "total_members": len(members),
            "members": members
        }
    )


# @router.post("/members/invite")
# def invite_user_to_organization(
#     email: str,
#     role: str = "member",
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Invite a user to YOUR organization by email

#     Creates an invitation that user can accept
#     """
#     from app.models.invitation import Invitation
#     import secrets

#     # Authorization: Must be an authenticated organization
#     if not isinstance(current_user, Organization):
#         raise HTTPException(
#             status_code=403,
#             detail="Only organizations can invite users"
#         )

#     org_id = current_user.id

#     # Validate role
#     valid_roles = ["admin", "manager", "member"]
#     if role not in valid_roles:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
#         )

#     # Check if user already exists
#     existing_user = db.query(User).filter(User.email == email).first()

#     if existing_user:
#         # Check if already a member
#         from app.models.user_organizations import UserOrganization
#         existing_membership = db.query(UserOrganization).filter(
#             UserOrganization.organization_id == org_id,
#             UserOrganization.user_id == existing_user.id
#         ).first()

#         if existing_membership:
#             raise HTTPException(
#                 status_code=400,
#                 detail="User is already a member of your organization"
#             )

#     # Create invitation
#     invitation_token = secrets.token_urlsafe(32)

#     invitation = Invitation(
#         email=email,
#         organization_id=org_id,
#         role=role,
#         token=invitation_token,
#         expires_at=datetime.utcnow() + timedelta(days=7)  # Valid for 7 days
#     )

#     db.add(invitation)
#     db.commit()
#     db.refresh(invitation)

#     return create_response(
#         success=True,
#         message=f"Invitation sent to {email}",
#         data={
#             "invitation_id": invitation.id,
#             "email": email,
#             "role": role,
#             "invitation_link": f"/accept-invitation?token={invitation_token}",
#             "expires_at": invitation.expires_at.isoformat()
#         }
#     )
