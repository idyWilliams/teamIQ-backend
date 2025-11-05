from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Union

from app.core.database import get_db
from app.core.security import get_current_organization, get_current_user_or_organization
from app.models.user import User
from app.models.organization import Organization
from app.models.project import Project, ProjectMember
from app.schemas.project import (
    ProjectDetailsCreate,
    PMToolSetup,
    VCSetup,
    CommToolSetup,
    UserPermissionSync,
    ProjectCreate,
    ProjectResponse,
    ProjectMemberAdd
)
from app.schemas.response_model import create_response
from app.repositories import project_repository


router = APIRouter()


# ------------------------
# STEP-BY-STEP ENDPOINTS
# ------------------------

@router.post("/create/step1-details")
def create_project_step1(
    project_data: ProjectDetailsCreate,
    db: Session = Depends(get_db),
    current_user: Organization = Depends(get_current_organization)
):
    """
    Step 1: Create project with basic details
    """
    # Only organizations can create projects
    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can create projects")

    organization_id = current_user.id
    owner_id = None # No owner at this stage
    project_lead_id = None # No project lead at this stage
    # Create initial project
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=owner_id,
        organization_id=organization_id,
        project_lead_id=project_lead_id,
        stacks=project_data.stacks,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        linked_documents=project_data.linked_documents,
        project_image=project_data.project_image,
        is_visible=project_data.is_visible
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return create_response(
        success=True,
        message="Project details saved successfully",
        data={"project_id": new_project.id, "project": ProjectResponse.model_validate(new_project)}
    )


@router.patch("/{project_id}/step2-pm-tool")
def update_project_pm_tool(
    project_id: int,
    pm_data: PMToolSetup,
    db: Session = Depends(get_db),
    current_user = Depends(

    )
):
    """
    Step 2: Configure Project Management Tool integration
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    if project.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    # Update PM tool settings
    project.pm_tool = pm_data.pm_tool
    project.pm_integration_method = pm_data.pm_integration_method
    project.pm_project_id = pm_data.pm_project_id
    project.pm_api_key = pm_data.pm_api_key
    project.pm_access_token = pm_data.pm_access_token

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message="Project management tool configured successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.patch("/{project_id}/step3-version-control")
def update_project_version_control(
    project_id: int,
    vc_data: VCSetup,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 3: Configure Version Control integration
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    if project.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    # Update VC settings
    project.vc_tool = vc_data.vc_tool
    project.vc_integration_method = vc_data.vc_integration_method
    project.vc_repository_url = vc_data.vc_repository_url
    project.vc_api_key = vc_data.vc_api_key
    project.vc_access_token = vc_data.vc_access_token

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message="Version control configured successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.patch("/{project_id}/step4-communication-tool")
def update_project_communication_tool(
    project_id: int,
    comm_data: CommToolSetup,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 4: Configure Communication Tool integration
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    if project.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    # Update communication tool settings
    project.comm_tool = comm_data.comm_tool
    project.comm_integration_method = comm_data.comm_integration_method
    project.comm_channel_id = comm_data.comm_channel_id
    project.comm_api_key = comm_data.comm_api_key
    project.comm_webhook_url = comm_data.comm_webhook_url
    project.comm_notifications = comm_data.comm_notifications

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message="Communication tool configured successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.post("/{project_id}/step5-add-members")
def add_project_members(
    project_id: int,
    members_data: UserPermissionSync,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 5: Add team members to the project
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    if project.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    # Clear existing members (optional - or check for duplicates)
    db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()

    # Add new members
    for member in members_data.members:
        project_member = ProjectMember(
            project_id=project_id,
            user_id=member.user_id,
            role=member.role
        )
        db.add(project_member)

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message="Team members added successfully",
        data=ProjectResponse.model_validate(project)
    )


# ------------------------
# ALL-IN-ONE ENDPOINT (Optional - for future use)
# ------------------------

@router.post("/create")
def create_complete_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Create a complete project with all steps in one request
    """
    if isinstance(current_user, User):
        organization_id = current_user.organization_id
        owner_id = current_user.id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
        owner_id = project_data.project_lead_id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    new_project = Project(
        # Step 1
        name=project_data.name,
        description=project_data.description,
        owner_id=owner_id,
        organization_id=organization_id,
        project_lead_id=project_data.project_lead_id,
        stacks=project_data.stacks,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
        linked_documents=project_data.linked_documents,
        project_image=project_data.project_image,
        is_visible=project_data.is_visible,

        # Step 2
        pm_tool=project_data.pm_tool,
        pm_integration_method=project_data.pm_integration_method,
        pm_project_id=project_data.pm_project_id,
        pm_api_key=project_data.pm_api_key,

        # Step 3
        vc_tool=project_data.vc_tool,
        vc_integration_method=project_data.vc_integration_method,
        vc_repository_url=project_data.vc_repository_url,
        vc_api_key=project_data.vc_api_key,

        # Step 4
        comm_tool=project_data.comm_tool,
        comm_integration_method=project_data.comm_integration_method,
        comm_channel_id=project_data.comm_channel_id,
        comm_api_key=project_data.comm_api_key,
        comm_webhook_url=project_data.comm_webhook_url,
        comm_notifications=project_data.comm_notifications
    )

    db.add(new_project)
    db.flush()  # Get project ID

    # Add members
    if project_data.member_ids:
        for user_id in project_data.member_ids:
            member = ProjectMember(project_id=new_project.id, user_id=user_id)
            db.add(member)

    db.commit()
    db.refresh(new_project)

    return create_response(
        success=True,
        message="Project created successfully",
        data=ProjectResponse.model_validate(new_project)
    )


# ------------------------
# UTILITY ENDPOINTS
# ------------------------

@router.get("/{project_id}")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    if project.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this project")

    return create_response(
        success=True,
        message="Project retrieved successfully",
        data=ProjectResponse.model_validate(project)
    )


@router.get("/")
def list_projects(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """List all projects for the current user's organization"""
    if isinstance(current_user, User):
        organization_id = current_user.organization_id
    elif isinstance(current_user, Organization):
        organization_id = current_user.id
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    projects = db.query(Project).filter(
        Project.organization_id == organization_id
    ).all()

    return create_response(
        success=True,
        message="Projects retrieved successfully",
        data=[ProjectResponse.model_validate(p) for p in projects]
    )
