from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict
import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class IntegrationMethod(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"


# Step 1: Project Details
class ProjectDetailsCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_lead_id: Optional[int] = None
    stacks: Optional[List[str]] = []
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    linked_documents: Optional[List[str]] = []
    project_image: Optional[str] = None
    is_visible: bool = True


# Step 2: Project Management Tool Setup
class PMToolSetup(BaseModel):
    pm_tool: Optional[str] = None
    pm_integration_method: Optional[IntegrationMethod] = None
    pm_project_id: Optional[str] = None
    pm_api_key: Optional[str] = None
    pm_access_token: Optional[str] = None


# Step 3: Version Control Setup
class VCSetup(BaseModel):
    vc_tool: Optional[str] = None
    vc_integration_method: Optional[IntegrationMethod] = None
    vc_repository_url: Optional[str] = None
    vc_api_key: Optional[str] = None
    vc_access_token: Optional[str] = None


# Step 4: Communication Tool Setup
class CommToolSetup(BaseModel):
    comm_tool: Optional[str] = None
    comm_integration_method: Optional[IntegrationMethod] = None
    comm_channel_id: Optional[str] = None
    comm_api_key: Optional[str] = None
    comm_webhook_url: Optional[str] = None
    comm_notifications: Optional[Dict[str, bool]] = {
        "pmt_updates": True,
        "code_events": True,
        "sentiment_monitoring": True,
        "custom_commands": True
    }


# Step 5: User & Permission Sync
class ProjectMemberAdd(BaseModel):
    user_id: int
    role: Optional[str] = None


class UserPermissionSync(BaseModel):
    members: List[ProjectMemberAdd]


# Complete Project Creation (All Steps)
class ProjectCreate(BaseModel):
    # Step 1
    name: str
    description: Optional[str] = None
    project_lead_id: Optional[int] = None
    stacks: Optional[List[str]] = []
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    linked_documents: Optional[List[str]] = []
    project_image: Optional[str] = None
    is_visible: bool = True

    # Step 2
    pm_tool: Optional[str] = None
    pm_integration_method: Optional[IntegrationMethod] = None
    pm_project_id: Optional[str] = None
    pm_api_key: Optional[str] = None

    # Step 3
    vc_tool: Optional[str] = None
    vc_integration_method: Optional[IntegrationMethod] = None
    vc_repository_url: Optional[str] = None
    vc_api_key: Optional[str] = None

    # Step 4
    comm_tool: Optional[str] = None
    comm_integration_method: Optional[IntegrationMethod] = None
    comm_channel_id: Optional[str] = None
    comm_api_key: Optional[str] = None
    comm_webhook_url: Optional[str] = None
    comm_notifications: Optional[Dict[str, bool]] = None

    # Step 5
    member_ids: Optional[List[int]] = []


# Response Models
class ProjectMemberResponse(BaseModel):
    id: int
    user_id: int
    role: Optional[str]

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: Optional[int]  
    organization_id: Optional[int]
    project_lead_id: Optional[int]
    stacks: Optional[List[str]]
    start_date: Optional[datetime.datetime]
    end_date: Optional[datetime.datetime]

    # Integration details
    pm_tool: Optional[str]
    vc_tool: Optional[str]
    comm_tool: Optional[str]

    status: ProjectStatus
    pct_complete: float
    is_visible: bool

    createdAt: datetime.datetime
    updatedAt: datetime.datetime

    class Config:
        from_attributes = True
