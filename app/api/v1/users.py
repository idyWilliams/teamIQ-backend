from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.organization import Organization, UserRole
from app.schemas.user import UserOut, UserUpdate
from app.repositories import user_repository
from app.core.database import get_db
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization


router = APIRouter()


@router.get("/organization/users")
def read_organization_users(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all users for the authenticated organization.
    Only accessible by organizations.
    """
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can access this endpoint")

    users = user_repository.get_users_by_organization(db, organization_id=current_user.id)
    users_out = [UserOut.model_validate(user) for user in users]

    return create_response(
        success=True,
        message="Users retrieved successfully",
        data=[user.model_dump() for user in users_out]
    )


@router.get("/organization/user/{user_id}")
def read_organization_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Allow an authenticated organization to view a specific user's details by ID.
    The organization can only view users that belong to them.
    """
    # Ensure the requester is an organization
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can access this endpoint")

    # Get the user from the organization
    db_user = (
        db.query(User)
        .options(joinedload(User.organization))
        .filter(User.id == user_id, User.organization_id == current_user.id)
        .first()
    )

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found in your organization")

    user_out = UserOut.model_validate(db_user)
    return create_response(
        success=True,
        message="User retrieved successfully",
        data=user_out.model_dump()
    )


@router.get("/{user_id}")
def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get a specific user's profile by ID.
    - Organizations can view their own users
    - Users can view their own profile
    - Mentors can view any user profile
    """
    db_user = db.query(User).options(joinedload(User.organization)).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Authorization check
    if isinstance(current_user, Organization):
        # Organization can only view users that belong to them
        if db_user.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied: User does not belong to your organization")

    elif isinstance(current_user, User):
        # User can view their own profile, or mentors can view any profile
        if current_user.id != user_id and current_user.role != UserRole.MENTOR:
            raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")

    else:
        raise HTTPException(status_code=403, detail="Access denied")

    user_out = UserOut.model_validate(db_user)
    return create_response(
        success=True,
        message="User retrieved successfully",
        data=user_out.model_dump()
    )


@router.put("/{user_id}")
def update_profile(
    user_id: int,
    user_update: UserUpdate,  # Use UserUpdate schema instead of dict
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Update user profile.
    Only the user themselves can update their own profile.
    """
    # Only users can update profiles, not organizations
    if not isinstance(current_user, User):
        raise HTTPException(status_code=403, detail="Only users can update profiles")

    # Users can only update their own profile
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Can only update your own profile")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update only the fields that are provided
    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_user, field, value)

    db.commit()
    db.refresh(db_user)

    user_out = UserOut.model_validate(db_user)
    return create_response(
        success=True,
        message="Profile updated successfully",
        data=user_out.model_dump()
    )

@router.get("/{user_id}/organizations")
def get_user_organizations(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    user = user_repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    orgs = user.organizations
    return create_response(
        success=True,
        message="User organizations retrieved successfully",
        data=[{"id": org.id, "organization_name": org.organization_name, "email": org.email, "organization_image": org.organization_image} for org in orgs]
    )
