"""
API endpoints for managing user-to-tool account mappings
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user_or_organization
from app.models.user import User
from app.models.organization import Organization
from app.models.project import Project, ProjectMember
from app.schemas.user_mapping import (
    UserMappingCreate,
    UserMappingDelete,
    UserMappingResponse
)
from app.services.user_mapping_service import UserMappingService
from app.utils.response import create_response

router = APIRouter()


def check_mapping_permission(
    db: Session,
    project_id: int,
    current_user
) -> bool:
    """
    Check if current user has permission to manage mappings
    - Organization owners can manage all mappings
    - Project owners can manage mappings in their projects
    """
    if isinstance(current_user, Organization):
        # Organization can manage all their projects
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.organization_id == current_user.id
        ).first()
        return project is not None

    elif isinstance(current_user, User):
        # Check if user is project owner
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id
        ).first()
        return project is not None

    return False


@router.post("/map")
async def map_user_to_account(
    mapping_data: UserMappingCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Map a TeamIQ user to an external tool account

    Requires: Project owner or organization owner permissions
    """
    # Check permissions
    if not check_mapping_permission(db, mapping_data.project_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to manage mappings for this project"
        )

    # Get user and project details for email
    user = db.query(User).filter(User.id == mapping_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == mapping_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Perform mapping
    result = UserMappingService.map_user_to_external_account(
        db=db,
        project_id=mapping_data.project_id,
        user_id=mapping_data.user_id,
        provider=mapping_data.provider,
        external_user_id=mapping_data.external_user_id,
        external_username=mapping_data.external_username,
        external_email=mapping_data.external_email,
        mapped_by_user_id=current_user.id
    )

    # Send email notification in background
    mapped_by_name = current_user.organization_name if isinstance(current_user, Organization) else f"{current_user.first_name} {current_user.last_name}"
    user_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username

    background_tasks.add_task(
        UserMappingService.send_mapping_notification,
        user_email=user.email,
        user_name=user_name,
        project_name=project.name,
        provider=mapping_data.provider,
        external_username=mapping_data.external_username or mapping_data.external_user_id,
        mapped_by=mapped_by_name
    )

    return create_response(
        success=True,
        message=f"User successfully mapped to {mapping_data.provider} account",
        data=result
    )


@router.delete("/unmap")
async def unmap_user_from_account(
    unmapping_data: UserMappingDelete,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Unmap a TeamIQ user from an external tool account

    Requires: Project owner, organization owner, or the user themselves
    """
    # Check permissions (users can unmap themselves)
    is_self = isinstance(current_user, User) and current_user.id == unmapping_data.user_id
    has_admin_permission = check_mapping_permission(db, unmapping_data.project_id, current_user)

    if not (is_self or has_admin_permission):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to unmap this user"
        )

    # Get user and project details for email
    user = db.query(User).filter(User.id == unmapping_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    project = db.query(Project).filter(Project.id == unmapping_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Perform unmapping
    result = UserMappingService.unmap_user_from_external_account(
        db=db,
        project_id=unmapping_data.project_id,
        user_id=unmapping_data.user_id,
        provider=unmapping_data.provider,
        reason=unmapping_data.reason
    )

    # Send email notification in background
    user_name = f"{user.first_name} {user.last_name}" if user.first_name else user.username

    background_tasks.add_task(
        UserMappingService.send_unmapping_notification,
        user_email=user.email,
        user_name=user_name,
        project_name=project.name,
        provider=unmapping_data.provider,
        reason=unmapping_data.reason
    )

    return create_response(
        success=True,
        message=f"User successfully unmapped from {unmapping_data.provider} account",
        data=result
    )


@router.get("/project/{project_id}/user/{user_id}")
def get_user_mappings_for_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all mappings for a specific user in a project

    Users can view their own mappings, admins can view all
    """
    # Check permissions
    is_self = isinstance(current_user, User) and current_user.id == user_id
    has_admin_permission = check_mapping_permission(db, project_id, current_user)

    if not (is_self or has_admin_permission):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view these mappings"
        )

    mappings = UserMappingService.get_user_mappings(db, project_id, user_id)

    return create_response(
        success=True,
        message="User mappings retrieved successfully",
        data=mappings
    )


@router.get("/{user_id}")
def get_all_user_mappings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all mappings for a user across all projects

    Users can only view their own mappings unless they're an organization
    """
    # Check permissions
    is_self = isinstance(current_user, User) and current_user.id == user_id
    is_org = isinstance(current_user, Organization)

    if not (is_self or is_org):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view these mappings"
        )

    mappings = UserMappingService.get_all_user_mappings(db, user_id)

    return create_response(
        success=True,
        message="All user mappings retrieved successfully",
        data=mappings
    )


@router.get("/project/{project_id}/all")
def get_all_project_mappings(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all user mappings for a project

    Requires: Project owner or organization owner permissions
    """
    # Check permissions
    if not check_mapping_permission(db, project_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view mappings for this project"
        )

    # Get all project members
    members = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id
    ).all()

    project = db.query(Project).filter(Project.id == project_id).first()

    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        if user:
            result.append({
                "user_id": user.id,
                "user_email": user.email,
                "user_name": f"{user.first_name} {user.last_name}" if user.first_name else user.username,
                "project_id": project_id,
                "project_name": project.name if project else None,
                "mappings": member.external_mappings or {}
            })

    return create_response(
        success=True,
        message="Project mappings retrieved successfully",
        data=result
    )
