from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

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
    ProjectResponse
)
from app.core.encryption import encrypt_field
from app.schemas.response_model import create_response, APIResponse
from app.services.webhook_secret_generator import generate_github_webhook_secret, generate_jira_webhook_secret, generate_slack_signing_secret
from app.services.webhook_service import get_webhook_service
from app.tasks.sync_scheduler import sync_single_project, get_scheduler_status
from app.repositories import project_repository
from app.schemas.user import UserOut
from typing import List

router = APIRouter()


# ------------------------
# NEW ENDPOINTS
# ------------------------

@router.get("/{project_id}/users", response_model=APIResponse[List[UserOut]])
def get_project_users(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Get all users assigned to a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized to view this project")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this project")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    users = project_repository.get_users_for_project(db, project_id=project_id)
    return create_response(
        success=True,
        message="Project users retrieved successfully",
        data=[UserOut.model_validate(user) for user in users]
    )


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

    if not isinstance(current_user, Organization):
        raise HTTPException(status_code=403, detail="Only organizations can create projects")

    organization_id = current_user.id
    owner_id = None
    project_lead_id = None

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


# @router.patch("/{project_id}/step2-pm-tool")
# def update_project_pm_tool(
#     project_id: int,
#     pm_data: PMToolSetup,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Step 2: Configure Project Management Tool integration
#     """
#     project = db.query(Project).filter(Project.id == project_id).first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")


#     if isinstance(current_user, User):
#         user_org_ids = [org.id for org in current_user.organizations]
#         if project.organization_id not in user_org_ids:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     elif isinstance(current_user, Organization):
#         if project.organization_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     else:
#         raise HTTPException(status_code=403, detail="Invalid user type")

#     # Update PM tool settings
#     # project.pm_tool = pm_data.pm_tool
#     # project.pm_integration_method = pm_data.pm_integration_method
#     # project.pm_project_id = pm_data.pm_project_id
#     # project.pm_api_key = pm_data.pm_api_key
#     # project.pm_access_token = pm_data.pm_access_token
#     # project.pm_workspace_url = pm_data.pm_workspace_url

#     # db.commit()
#     # db.refresh(project)

#     # return create_response(
#     #     success=True,
#     #     message="Project management tool configured successfully",
#     #     data=ProjectResponse.model_validate(project)
#     # )
#     project.pm_tool = pm_data.pm_tool
#     project.pm_integration_method = pm_data.pm_integration_method
#     project.pm_project_id = pm_data.pm_project_id
#     project.pm_workspace_url = pm_data.pm_workspace_url

#     # ENCRYPT API key
#     if pm_data.pm_api_key:
#         project.pm_api_key = encrypt_field(pm_data.pm_api_key)

#     # For Jira, store email for Basic Auth
#     if pm_data.pm_tool == "jira" and pm_data.email:
#         project.pm_email = encrypt_field(pm_data.email)

#     db.commit()
#     db.refresh(project)

#     return create_response(
#         success=True,
#         message="Jira configured successfully",
#         data=ProjectResponse.model_validate(project)
#     )

# @router.patch("/{project_id}/step3-version-control")
# def update_project_version_control(
#     project_id: int,
#     vc_data: VCSetup,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Step 3: Configure Version Control integration
#     """
#     project = db.query(Project).filter(Project.id == project_id).first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")


#     if isinstance(current_user, User):
#         user_org_ids = [org.id for org in current_user.organizations]
#         if project.organization_id not in user_org_ids:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     elif isinstance(current_user, Organization):
#         if project.organization_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     else:
#         raise HTTPException(status_code=403, detail="Invalid user type")

#     # Update VC settings
#     project.vc_tool = vc_data.vc_tool
#     project.vc_integration_method = vc_data.vc_integration_method
#     project.vc_repository_url = vc_data.vc_repository_url
#     project.vc_api_key = vc_data.vc_api_key
#     project.vc_access_token = vc_data.vc_access_token

#     db.commit()
#     db.refresh(project)

#     return create_response(
#         success=True,
#         message="Version control configured successfully",
#         data=ProjectResponse.model_validate(project)
#     )


# @router.patch("/{project_id}/step4-communication-tool")
# def update_project_communication_tool(
#     project_id: int,
#     comm_data: CommToolSetup,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Step 4: Configure Communication Tool integration
#     """
#     project = db.query(Project).filter(Project.id == project_id).first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")


#     if isinstance(current_user, User):
#         user_org_ids = [org.id for org in current_user.organizations]
#         if project.organization_id not in user_org_ids:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     elif isinstance(current_user, Organization):
#         if project.organization_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     else:
#         raise HTTPException(status_code=403, detail="Invalid user type")

#     # Update communication tool settings
#     project.comm_tool = comm_data.comm_tool
#     project.comm_integration_method = comm_data.comm_integration_method
#     project.comm_channel_id = comm_data.comm_channel_id
#     project.comm_api_key = comm_data.comm_api_key
#     project.comm_webhook_url = comm_data.comm_webhook_url
#     project.comm_notifications = comm_data.comm_notifications

#     db.commit()
#     db.refresh(project)

#     return create_response(
#         success=True,
#         message="Communication tool configured successfully",
#         data=ProjectResponse.model_validate(project)
#     )


# @router.patch("/{project_id}/step5-add-members")
# def add_project_members(
#     project_id: int,
#     members_data: UserPermissionSync,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Step 5: Add team members to the project
#     """
#     project = db.query(Project).filter(Project.id == project_id).first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")


#     if isinstance(current_user, User):
#         user_org_ids = [org.id for org in current_user.organizations]
#         if project.organization_id not in user_org_ids:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     elif isinstance(current_user, Organization):
#         if project.organization_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this project")
#     else:
#         raise HTTPException(status_code=403, detail="Invalid user type")

#     db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()


#     for member in members_data.members:
#         project_member = ProjectMember(
#             project_id=project_id,
#             user_id=member.user_id,
#             role=member.role
#         )
#         db.add(project_member)

#     db.commit()
#     db.refresh(project)

#     return create_response(
#         success=True,
#         message="Team members added successfully",
#         data=ProjectResponse.model_validate(project)
#     )

# @router.patch("/{project_id}/step5-add-members")
# def add_project_members_and_sync(
#     project_id: int,
#     members_data: UserPermissionSync,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
#     current_user = Depends(get_current_user_or_organization)
# ):
#     """
#     Step 5: Add team members to project and trigger initial sync
#     This pulls all tasks, commits, and activities from external tools
#     """
#     project = db.query(Project).filter(Project.id == project_id).first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")

#     # Authorization check
#     if isinstance(current_user, User):
#         user_org_ids = [org.id for org in current_user.organizations]
#         if project.organization_id not in user_org_ids:
#             raise HTTPException(status_code=403, detail="Not authorized")
#     elif isinstance(current_user, Organization):
#         if project.organization_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized")
#     else:
#         raise HTTPException(status_code=403, detail="Invalid user type")

#     # Clear existing members
#     db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()

#     # Add new members
#     for member in members_data.members:
#         project_member = ProjectMember(
#             project_id=project_id,
#             user_id=member.user_id,
#             role=member.role
#         )
#         db.add(project_member)

#     db.commit()
#     db.refresh(project)

#     #   INITIAL SYNC IN BACKGROUND
#     # background_tasks.add_task(perform_initial_project_sync, project_id, db)

#     webhook_service = get_webhook_service(db)
#     webhook_service.initialize_webhooks_for_project(project_id)

#     # Trigger initial sync
#     background_tasks.add_task(perform_initial_project_sync, project_id, db)

#     return create_response(
#         success=True,
#         message="Setup complete! Configure webhooks for real-time sync.",
#         data={
#             "project": ProjectResponse.model_validate(project),
#             "next_step": f"/api/v1/projects/{project_id}/webhook-setup-instructions"
#         }
#     )


# ==============================================================================
# STEP 2: PROJECT MANAGEMENT TOOL
# ==============================================================================

@router.patch("/{project_id}/step2-pm-tool")
def update_project_pm_tool(
    project_id: int,
    pm_data: PMToolSetup,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 2: Configure Project Management Tool integration
    Auto-generates webhook secret for security
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    # ✅ VALIDATE configuration
    # try:
    #     validated = validate_tool_config(
    #         "project_management",
    #         pm_data.pm_tool.value,
    #         pm_data.dict()
    #     )
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Invalid configuration: {str(e)}"
    #     )

    # Update PM tool settings
    project.pm_tool = pm_data.pm_tool.value
    project.pm_integration_method = pm_data.pm_integration_method
    project.pm_project_id = pm_data.pm_project_id
    project.pm_workspace_url = pm_data.pm_workspace_url

    # ✅ ENCRYPT sensitive fields
    if pm_data.pm_api_key:
        project.pm_api_key = encrypt_field(pm_data.pm_api_key)

    if pm_data.pm_access_token:
        project.pm_access_token = encrypt_field(pm_data.pm_access_token)

    # For Jira/Bitbucket: Store email for Basic Auth
    if pm_data.email and pm_data.pm_tool.value in ["jira", "bitbucket"]:
        project.pm_email = encrypt_field(pm_data.email)

    # ✅ AUTO-GENERATE webhook secret
    webhook_secret = generate_jira_webhook_secret()
    project.pm_webhook_secret = encrypt_field(webhook_secret)
    print(f"✅ Generated PM webhook secret for project {project_id}")

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message=f"{pm_data.pm_tool.value.capitalize()} configured successfully",
        data=ProjectResponse.model_validate(project)
    )


# ==============================================================================
# STEP 3: VERSION CONTROL
# ==============================================================================

@router.patch("/{project_id}/step3-version-control")
def update_project_version_control(
    project_id: int,
    vc_data: VCSetup,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 3: Configure Version Control integration
    Auto-generates webhook secret if not provided
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    # ✅ VALIDATE configuration
    # try:
    #     validated = validate_tool_config(
    #         "version_control",
    #         vc_data.vc_tool.value,
    #         vc_data.dict()
    #     )
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Invalid configuration: {str(e)}"
    #     )

    # Update VC settings
    project.vc_tool = vc_data.vc_tool.value
    project.vc_integration_method = vc_data.vc_integration_method
    project.vc_repository_url = vc_data.vc_repository_url

    # ✅ ENCRYPT credentials
    if vc_data.vc_access_token:
        project.vc_access_token = encrypt_field(vc_data.vc_access_token)

    if vc_data.vc_api_key:
        project.vc_api_key = encrypt_field(vc_data.vc_api_key)

    if vc_data.email:  # For Bitbucket
        project.vc_email = encrypt_field(vc_data.email)

    # ✅ AUTO-GENERATE WEBHOOK SECRET if not provided
    if vc_data.vc_webhook_secret:
        # User provided their own secret
        project.vc_webhook_secret = encrypt_field(vc_data.vc_webhook_secret)
    else:
        # Generate secure secret automatically
        generated_secret = generate_github_webhook_secret()
        project.vc_webhook_secret = encrypt_field(generated_secret)
        print(f"✅ Generated VC webhook secret for project {project_id}")

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message=f"{vc_data.vc_tool.value.capitalize()} configured successfully",
        data=ProjectResponse.model_validate(project)
    )


# ==============================================================================
# STEP 4: COMMUNICATION TOOL
# ==============================================================================

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

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    # # ✅ VALIDATE configuration
    # try:
    #     validated = validate_tool_config(
    #         "communication",
    #         comm_data.comm_tool.value,
    #         comm_data.dict()
    #     )
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Invalid configuration: {str(e)}"
    #     )

    # Update communication tool settings
    project.comm_tool = comm_data.comm_tool.value
    project.comm_integration_method = comm_data.comm_integration_method
    project.comm_channel_id = comm_data.comm_channel_id
    project.comm_webhook_url = comm_data.comm_webhook_url
    project.comm_notifications = comm_data.comm_notifications

    # ✅ ENCRYPT API key
    if comm_data.comm_api_key:
        project.comm_api_key = encrypt_field(comm_data.comm_api_key)

    # Teams-specific fields
    if comm_data.comm_tool.value == "teams":
        if hasattr(comm_data, 'client_id') and comm_data.client_id:
            project.teams_client_id = comm_data.client_id
        if hasattr(comm_data, 'tenant_id') and comm_data.tenant_id:
            project.teams_tenant_id = comm_data.tenant_id

    # ✅ AUTO-GENERATE webhook secret for Slack
    if comm_data.comm_tool.value == "slack":
        webhook_secret = generate_slack_signing_secret()
        project.comm_webhook_secret = encrypt_field(webhook_secret)
        print(f"✅ Generated Slack signing secret for project {project_id}")

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message=f"{comm_data.comm_tool.value.capitalize()} configured successfully",
        data=ProjectResponse.model_validate(project)
    )


# ==============================================================================
# STEP 5: ADD MEMBERS & TRIGGER INITIAL SYNC
# ==============================================================================

@router.patch("/{project_id}/step5-add-members")
def add_project_members_and_sync(
    project_id: int,
    members_data: UserPermissionSync,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Step 5: Add team members to project and trigger initial sync
    This pulls all tasks, commits, and activities from external tools
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    # Clear existing members
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

    # ✅ INITIALIZE webhook tracking
    webhook_service = get_webhook_service(db)
    webhook_service.initialize_webhooks_for_project(project_id)

    # ✅ TRIGGER initial sync in background
    background_tasks.add_task(perform_initial_project_sync, project_id, db)

    return create_response(
        success=True,
        message="Setup complete! Configure webhooks for real-time sync.",
        data={
            "project": ProjectResponse.model_validate(project),
            "next_step": f"/api/v1/projects/{project_id}/webhook-setup-instructions"
        }
    )


def perform_initial_project_sync(project_id: int, db: Session):
    """
    Perform initial sync after project creation
    Pulls: Tasks, Commits, Messages, Maps Users
    """
    from app.services.initial_sync import InitialProjectSync

    try:
        sync_service = InitialProjectSync(project_id, db)
        results = sync_service.sync_all()

        print(f"✅ Initial sync completed for project {project_id}")
        print(f"   Tasks synced: {results.get('tasks_synced', 0)}")
        print(f"   Commits synced: {results.get('commits_synced', 0)}")
        print(f"   Activities synced: {results.get('activities_synced', 0)}")
        print(f"   Users mapped: {results.get('users_mapped', 0)}")

    except Exception as e:
        print(f"❌ Initial sync failed for project {project_id}: {str(e)}")


def perform_initial_project_sync(project_id: int, db: Session):
    """
    Perform initial sync after project creation
    Pulls:
    - Tasks from Jira/ClickUp
    - Commits from GitHub/GitLab
    - Messages from Slack/Discord
    - Maps external users to TeamIQ users
    """
    from app.services.initial_sync import InitialProjectSync

    try:
        sync_service = InitialProjectSync(project_id, db)
        results = sync_service.sync_all()

        print(f"✅ Initial sync completed for project {project_id}")
        print(f"   Tasks synced: {results.get('tasks_synced', 0)}")
        print(f"   Commits synced: {results.get('commits_synced', 0)}")
        print(f"   Activities synced: {results.get('activities_synced', 0)}")
        print(f"   Users mapped: {results.get('users_mapped', 0)}")

    except Exception as e:
        print(f"❌ Initial sync failed for project {project_id}: {str(e)}")

# ------------------------
# ALL-IN-ONE ENDPOINT (Optional)
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
        user_org_ids = [org.id for org in current_user.organizations]
        if not user_org_ids:
            raise HTTPException(status_code=403, detail="User not associated with any organization")
        organization_id = user_org_ids[0]  # Use first organization
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
    db.flush()

    # Add members
    if project_data.member_ids:
        for user_id in project_data.member_ids:
            member = ProjectMember(project_id=new_project.id, user_id=user_id)
            db.add(member)

    db.commit()
    db.refresh(new_project)

    # Trigger initial sync
    sync_single_project(new_project.id)

    return create_response(
        success=True,
        message="Project created successfully and initial sync started",
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
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized to view this project")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this project")
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

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
        user_org_ids = [org.id for org in current_user.organizations]
        projects = db.query(Project).filter(
            Project.organization_id.in_(user_org_ids)
        ).all()
    elif isinstance(current_user, Organization):
        projects = db.query(Project).filter(
            Project.organization_id == current_user.id
        ).all()
    else:
        raise HTTPException(status_code=403, detail="Invalid user type")

    return create_response(
        success=True,
        message="Projects retrieved successfully",
        data=[ProjectResponse.model_validate(p) for p in projects]
    )




@router.post("/{project_id}/sync-now")
def trigger_immediate_sync(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Manually trigger integration sync for a specific project
    Useful for testing or immediate updates
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Trigger sync
    results = sync_single_project(project_id)

    return create_response(
        success="error" not in str(results),
        message="Integration sync completed",
        data=results
    )



@router.get("/{project_id}/webhook-health")
def get_webhook_health_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get real-time webhook health status
    Shows which webhooks are working, which need setup

    Used in project settings page
    """
    webhook_service = get_webhook_service(db)
    health = webhook_service.get_webhook_health(project_id)

    return create_response(
        success=True,
        message="Webhook health retrieved",
        data=health
    )


@router.get("/scheduler/status")
def get_sync_scheduler_status(
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get status of the background sync scheduler
    Admin/debugging endpoint
    """
    status = get_scheduler_status()

    return create_response(
        success=True,
        message="Scheduler status retrieved",
        data=status
    )

@router.get("/{project_id}/webhook-setup-instructions")
def get_webhook_setup_instructions(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Returns webhook setup instructions based on integrated tools
    Called after Step 5 completion

    Frontend displays these instructions to user
    User follows steps to configure webhooks in external tools
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    instructions = {
        "project_id": project_id,
        "project_name": project.name,
        "webhook_base_url": "https://teamiq.com/api/v1/webhooks",
        "instructions": []
    }

    # =========================================================================
    # JIRA WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.pm_tool == "jira":
        instructions["instructions"].append({
            "tool": "jira",
            "tool_name": "Jira",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/jira",
            "title": "Configure Jira Webhook for Real-Time Sync",
            "steps": [
                {
                    "step": 1,
                    "description": "Go to your Jira workspace",
                    "url": f"https://{project.pm_workspace_url}",
                    "action": "Open Jira"
                },
                {
                    "step": 2,
                    "description": "Click Settings ⚙️ → System → WebHooks",
                    "note": "You need admin permissions"
                },
                {
                    "step": 3,
                    "description": "Click 'Create a WebHook'"
                },
                {
                    "step": 4,
                    "description": "Configure webhook settings",
                    "fields": {
                        "Name": "TeamIQ Sync",
                        "Status": "Enabled",
                        "URL": "https://teamiq.com/api/v1/webhooks/jira",
                        "Description": f"Syncs project {project.name} with TeamIQ"
                    }
                },
                {
                    "step": 5,
                    "description": "Select events to trigger webhook",
                    "events": [
                        "✅ Issue → created",
                        "✅ Issue → updated",
                        "✅ Issue → deleted",
                        "✅ Comment → created"
                    ]
                },
                {
                    "step": 6,
                    "description": "Click 'Create' to save webhook"
                },
                {
                    "step": 7,
                    "description": "Test the webhook",
                    "test": "Create or update an issue in Jira. It should appear in TeamIQ within seconds."
                }
            ],
            "docs": "https://developer.atlassian.com/server/jira/platform/webhooks/",
            "video": "https://youtu.be/jira-webhook-setup"
        })

    # =========================================================================
    # CLICKUP WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.pm_tool == "clickup":
        instructions["instructions"].append({
            "tool": "clickup",
            "tool_name": "ClickUp",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/clickup",
            "title": "Configure ClickUp Webhook",
            "steps": [
                {
                    "step": 1,
                    "description": "Go to ClickUp Settings",
                    "url": "https://app.clickup.com/settings"
                },
                {
                    "step": 2,
                    "description": "Click 'Integrations' in sidebar"
                },
                {
                    "step": 3,
                    "description": "Scroll to 'Webhooks' section"
                },
                {
                    "step": 4,
                    "description": "Click '+ Webhook'"
                },
                {
                    "step": 5,
                    "description": "Configure webhook",
                    "fields": {
                        "Name": "TeamIQ Sync",
                        "Endpoint": "https://teamiq.com/api/v1/webhooks/clickup",
                        "Workspace": "Select your workspace"
                    }
                },
                {
                    "step": 6,
                    "description": "Select events",
                    "events": [
                        "✅ taskCreated",
                        "✅ taskUpdated",
                        "✅ taskDeleted",
                        "✅ taskCommentPosted"
                    ]
                },
                {
                    "step": 7,
                    "description": "Save webhook"
                }
            ],
            "docs": "https://docs.clickup.com/en/articles/1367147-webhooks"
        })

    # =========================================================================
    # GITHUB WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.vc_tool == "github":
        repo_name = project.vc_repository_url.split("/")[-1] if project.vc_repository_url else "your-repo"

        instructions["instructions"].append({
            "tool": "github",
            "tool_name": "GitHub",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/github",
            "title": "Configure GitHub Webhook for Real-Time Updates",
            "steps": [
                {
                    "step": 1,
                    "description": "Go to your GitHub repository",
                    "url": project.vc_repository_url,
                    "action": "Open Repository"
                },
                {
                    "step": 2,
                    "description": "Click 'Settings' tab"
                },
                {
                    "step": 3,
                    "description": "Click 'Webhooks' in left sidebar"
                },
                {
                    "step": 4,
                    "description": "Click 'Add webhook' button"
                },
                {
                    "step": 5,
                    "description": "Configure webhook settings",
                    "fields": {
                        "Payload URL": "https://teamiq.com/api/v1/webhooks/github",
                        "Content type": "application/json",
                        # "Secret": f"(Optional) Use: {settings.GITHUB_WEBHOOK_SECRET[:10]}..." if hasattr(settings, 'GITHUB_WEBHOOK_SECRET') else "(Optional - leave empty)"
                    }
                },
                {
                    "step": 6,
                    "description": "Select events to trigger webhook",
                    "events": [
                        "✅ Pushes (commits)",
                        "✅ Pull requests",
                        "✅ Issues",
                        "✅ Issue comments"
                    ],
                    "note": "Select 'Let me select individual events' option"
                },
                {
                    "step": 7,
                    "description": "Ensure webhook is Active",
                    "checkbox": "✅ Active"
                },
                {
                    "step": 8,
                    "description": "Click 'Add webhook'"
                },
                {
                    "step": 9,
                    "description": "Test the webhook",
                    "test": "Push a commit or create a PR. It should appear in TeamIQ dashboard immediately."
                }
            ],
            "docs": "https://docs.github.com/en/webhooks-and-events/webhooks/creating-webhooks",
            "video": "https://youtu.be/github-webhook-setup"
        })

    # =========================================================================
    # GITLAB WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.vc_tool == "gitlab":
        instructions["instructions"].append({
            "tool": "gitlab",
            "tool_name": "GitLab",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/gitlab",
            "title": "Configure GitLab Webhook",
            "steps": [
                {
                    "step": 1,
                    "description": "Go to your GitLab repository",
                    "url": project.vc_repository_url
                },
                {
                    "step": 2,
                    "description": "Click Settings → Webhooks"
                },
                {
                    "step": 3,
                    "description": "Configure webhook",
                    "fields": {
                        "URL": "https://teamiq.com/api/v1/webhooks/gitlab",
                        "Secret token": "(Optional)"
                    }
                },
                {
                    "step": 4,
                    "description": "Select trigger events",
                    "events": [
                        "✅ Push events",
                        "✅ Merge request events",
                        "✅ Issues events",
                        "✅ Comments"
                    ]
                },
                {
                    "step": 5,
                    "description": "Click 'Add webhook'"
                }
            ],
            "docs": "https://docs.gitlab.com/ee/user/project/integrations/webhooks.html"
        })

    # =========================================================================
    # SLACK WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.comm_tool == "slack":
        instructions["instructions"].append({
            "tool": "slack",
            "tool_name": "Slack",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/slack/events",
            "title": "Configure Slack Event Subscriptions",
            "note": "⚠️ Important: You must have already created a Slack App in Step 4",
            "steps": [
                {
                    "step": 1,
                    "description": "Go to your Slack App settings",
                    "url": "https://api.slack.com/apps",
                    "action": "Open Slack Apps"
                },
                {
                    "step": 2,
                    "description": "Select your TeamIQ Bot app"
                },
                {
                    "step": 3,
                    "description": "Click 'Event Subscriptions' in sidebar"
                },
                {
                    "step": 4,
                    "description": "Toggle 'Enable Events' to ON",
                    "toggle": "ON"
                },
                {
                    "step": 5,
                    "description": "Enter Request URL",
                    "fields": {
                        "Request URL": "https://teamiq.com/api/v1/webhooks/slack/events"
                    },
                    "note": "Slack will verify this URL. You'll see a green checkmark if successful."
                },
                {
                    "step": 6,
                    "description": "Subscribe to bot events",
                    "events": [
                        "✅ message.channels",
                        "✅ reaction_added",
                        "✅ file_shared",
                        "✅ app_mention"
                    ]
                },
                {
                    "step": 7,
                    "description": "Click 'Save Changes' at bottom"
                },
                {
                    "step": 8,
                    "description": "Reinstall app to workspace",
                    "note": "Slack will prompt you to reinstall after changing events"
                },
                {
                    "step": 9,
                    "description": "Test the webhook",
                    "test": f"Send a message in #{project.comm_channel_id}. It should appear in TeamIQ activity feed."
                }
            ],
            "docs": "https://api.slack.com/events",
            "video": "https://youtu.be/slack-events-setup"
        })

    # =========================================================================
    # DISCORD WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.comm_tool == "discord":
        instructions["instructions"].append({
            "tool": "discord",
            "tool_name": "Discord",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/discord",
            "title": "Configure Discord Webhook",
            "note": "Discord bot must be added to server (completed in Step 4)",
            "steps": [
                {
                    "step": 1,
                    "description": "Your Discord bot is already listening for events",
                    "note": "No additional webhook configuration needed!"
                },
                {
                    "step": 2,
                    "description": "Test the integration",
                    "test": "Send a message in your Discord channel. It should appear in TeamIQ within seconds."
                }
            ],
            "alternative": {
                "title": "Optional: Create Outgoing Webhook (for notifications)",
                "steps": [
                    {
                        "step": 1,
                        "description": "Go to Discord Server Settings"
                    },
                    {
                        "step": 2,
                        "description": "Click Integrations → Webhooks"
                    },
                    {
                        "step": 3,
                        "description": "Create webhook for TeamIQ notifications"
                    }
                ]
            },
            "docs": "https://discord.com/developers/docs/resources/webhook"
        })

    # =========================================================================
    # MICROSOFT TEAMS WEBHOOK INSTRUCTIONS
    # =========================================================================
    if project.comm_tool == "teams":
        instructions["instructions"].append({
            "tool": "teams",
            "tool_name": "Microsoft Teams",
            "webhook_url": "https://teamiq.com/api/v1/webhooks/teams",
            "title": "Configure Microsoft Teams Webhook",
            "note": "Azure AD app must be registered (completed in Step 4)",
            "steps": [
                {
                    "step": 1,
                    "description": "Teams integration uses Microsoft Graph API",
                    "note": "Webhooks are configured via Azure subscriptions"
                },
                {
                    "step": 2,
                    "description": "Go to Azure Portal",
                    "url": "https://portal.azure.com"
                },
                {
                    "step": 3,
                    "description": "Navigate to your registered app"
                },
                {
                    "step": 4,
                    "description": "Ensure API permissions are granted",
                    "permissions": [
                        "ChannelMessage.Read.All",
                        "Channel.ReadBasic.All"
                    ]
                },
                {
                    "step": 5,
                    "description": "TeamIQ will poll for messages automatically",
                    "note": "Real-time webhooks for Teams require additional Graph subscriptions"
                }
            ],
            "docs": "https://docs.microsoft.com/en-us/graph/webhooks"
        })

    # Add summary
    instructions["summary"] = {
        "total_webhooks": len(instructions["instructions"]),
        "estimated_time": f"{len(instructions['instructions']) * 5} minutes",
        "importance": "🔔 Webhooks enable real-time sync. Without them, data syncs every 15 minutes only.",
        "help": "Need help? Contact support@teamiq.com"
    }

    return create_response(
        success=True,
        message="Webhook setup instructions retrieved",
        data=instructions
    )

        #

@router.put("/{project_id}")
def update_project(
    project_id: int,
    project_update: ProjectCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Update/Edit an existing project

    Only project owner or organization admin can edit
    """
    from app.models.project import Project

    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        # User must be project owner
        if project.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only project owner can edit")

    elif isinstance(current_user, Organization):
        # Organization must own the project
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Project not in your organization")

    # Update fields
    update_data = project_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(project, field):
            setattr(project, field, value)

    project.updatedAt = datetime.utcnow()

    db.commit()
    db.refresh(project)

    return create_response(
        success=True,
        message="Project updated successfully",
        data={"project_id": project.id, "name": project.name}
    )


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Delete a project

    Only organization admin can delete projects
    This will also delete all associated data (tasks, members, etc.)
    """
    from app.models.project import Project, ProjectMember
    from app.models.task import Task

    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization: Only organization can delete
    if not isinstance(current_user, Organization):
        raise HTTPException(
            status_code=403,
            detail="Only organization admins can delete projects"
        )

    if project.organization_id != current_user.id:
        raise HTTPException(status_code=403, detail="Project not in your organization")

    # Delete associated data
    # 1. Delete all project members
    db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()

    # 2. Delete all tasks
    db.query(Task).filter(Task.project_id == project_id).delete()

    # 3. Delete the project
    db.delete(project)
    db.commit()

    return create_response(
        success=True,
        message=f"Project '{project.name}' deleted successfully",
        data={"project_id": project_id}
    )


@router.delete("/{project_id}/members/{user_id}")
def remove_user_from_project(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Remove a user from a project

    Only organization admin or project owner can remove users
    """
    from app.models.project import Project, ProjectMember

    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    authorized = False

    if isinstance(current_user, Organization):
        # Organization owns the project
        if project.organization_id == current_user.id:
            authorized = True

    elif isinstance(current_user, User):
        # User is project owner
        if project.owner_id == current_user.id:
            authorized = True

    if not authorized:
        raise HTTPException(
            status_code=403,
            detail="Only organization admin or project owner can remove members"
        )

    # Find and delete membership
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not in this project")

    # Get user name for response
    user = db.query(User).filter(User.id == user_id).first()
    user_name = f"{user.first_name} {user.last_name}" if user else "User"

    db.delete(membership)
    db.commit()

    return create_response(
        success=True,
        message=f"{user_name} removed from project successfully",
        data={"user_id": user_id, "project_id": project_id}
    )
