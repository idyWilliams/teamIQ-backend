from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta
from enum import Enum


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ON_HOLD = "on_hold"


class ProjectType(str, Enum):
    SOFTWARE_DEVELOPMENT = "software_development"
    BUSINESS_MANAGEMENT = "business_management"
    STRATEGY_CONSULTING = "strategy_consulting"
    MARKETING_CREATIVE = "marketing_creative"
    RESEARCH_DEVELOPMENT = "research_development"
    OTHER = "other"


class IntegrationMethod(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    WEBHOOK = "webhook"


class VCTool(str, Enum):
    """Version control tools"""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


# Step 1: Project Details
class ProjectDetailsCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.SOFTWARE_DEVELOPMENT
    industry: Optional[str] = None
    methodology: Optional[str] = None
    project_lead_id: Optional[int] = None
    stacks: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    linked_documents: List[Dict] = []
    project_image: Optional[str] = None
    is_visible: bool = True


# Step 2: Project Management Tool Setup
class PMToolSetup(BaseModel):
    pm_tool: str  # ✅ Required
    pm_integration_method: IntegrationMethod  # ✅ Required
    pm_project_id: Optional[str] = None
    pm_api_key: Optional[str] = None
    pm_access_token: Optional[str] = None
    pm_workspace_url: Optional[str] = None


# Step 3: Version Control Setup
class VCSetup(BaseModel):
    """Step 3: Configure version control"""
    vc_tool: VCTool  # ✅ Required
    vc_integration_method: IntegrationMethod  # ✅ Required
    vc_repository_url: str  # ✅ Required
    vc_api_key: Optional[str] = None
    vc_access_token: Optional[str] = None
    email: Optional[str] = None
    vc_webhook_secret: Optional[str] = Field(None, description="Webhook secret")


# Step 4: Communication Tool Setup
class CommToolSetup(BaseModel):
    comm_tool: str  # ✅ Required
    comm_integration_method: IntegrationMethod  # ✅ Required
    comm_channel_id: Optional[str] = None
    comm_api_key: Optional[str] = None
    comm_webhook_url: Optional[str] = None
    comm_notifications: Dict[str, bool] = Field(
        default_factory=lambda: {
            "pmt_updates": True,
            "code_events": True,
            "sentiment_monitoring": True,
            "custom_commands": True
        }
    )


# Step 5: User & Permission Sync
class ProjectMemberAdd(BaseModel):
    user_id: int = Field(..., alias="userId")
    role: Optional[str] = None
    external_mappings: Optional[Dict[str, str]] = Field(None, alias="externalMappings")

    class Config:
        populate_by_name = True


class UserPermissionSync(BaseModel):
    members: List[ProjectMemberAdd]


# Resource schemas (must be defined before ProjectCreate)
class ProjectResourceCreate(BaseModel):
    connectionId: int
    resourceId: str
    resourceType: str
    resourceName: str
    metadata: Optional[Dict] = None


# Complete Project Creation (All Steps)
class ProjectCreate(BaseModel):
    # Step 1: Required
    name: str
    description: Optional[str] = None
    project_type: ProjectType = ProjectType.SOFTWARE_DEVELOPMENT
    industry: Optional[str] = None
    methodology: Optional[str] = None
    project_lead_id: Optional[int] = None
    stacks: List[str] = []
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    linked_documents: List[Dict] = []
    project_image: Optional[str] = None
    is_visible: bool = True

    # Step 2: Optional
    pm_tool: Optional[str] = None
    pm_integration_method: Optional[IntegrationMethod] = None
    pm_project_id: Optional[str] = None
    pm_api_key: Optional[str] = None

    # Step 3: Optional
    vc_tool: Optional[str] = None
    vc_integration_method: Optional[IntegrationMethod] = None
    vc_repository_url: Optional[str] = None
    vc_api_key: Optional[str] = None

    # Step 4: Optional
    comm_tool: Optional[str] = None
    comm_integration_method: Optional[IntegrationMethod] = None
    comm_channel_id: Optional[str] = None
    comm_api_key: Optional[str] = None
    comm_webhook_url: Optional[str] = None
    comm_notifications: Optional[Dict[str, bool]] = None

    # Step 5
    members: List[ProjectMemberAdd] = []

    # Resources (New)
    resources: List[ProjectResourceCreate] = []



# Response Models
class ProjectMemberResponse(BaseModel):
    id: int
    user_id: int
    role: Optional[str]
    external_mappings: Optional[Dict[str, str]] = None

    model_config = {"from_attributes": True}


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    project_type: ProjectType
    industry: Optional[str] = None
    methodology: Optional[str] = None
    project_image_url: Optional[str] = None # Alias for project_image
    visibility: str = "public" # "public" or "private"
    owner_id: Optional[int]
    organization_id: Optional[int]
    project_lead_id: Optional[int]
    project_lead_name: Optional[str] = None
    stacks: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    current_milestone: Optional[str] = "Initial Development"
    linked_documents: List[Dict] = []

    # Integration details
    pm_tool: Optional[str]
    vc_tool: Optional[str]
    comm_tool: Optional[str]

    status: Optional[ProjectStatus] = None
    completion_percentage: float = 0.0 # Alias for pct_complete
    pct_complete: float
    is_visible: bool

    createdAt: datetime
    updatedAt: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProjectResourceResponse(BaseModel):
    id: int
    project_id: int
    connection_id: int
    resource_id: str
    resource_type: str
    resource_name: str
    resource_metadata: Optional[Dict] = None

    model_config = {"from_attributes": True}


# Enhanced response schemas for list endpoint
class ProjectMemberDetail(BaseModel):
    """Enhanced member information including user details"""
    id: int
    user_id: int
    user_name: str
    user_email: str
    user_avatar: Optional[str] = None
    role: Optional[str] = None
    external_mappings: Optional[Dict[str, str]] = None

    model_config = {"from_attributes": True}


class IntegratedAppDetail(BaseModel):
    """Information about integrated apps/resources"""
    id: int
    resource_name: str
    resource_type: str
    provider: str
    connection_id: int
    logo_url: Optional[str] = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class ProjectListItemResponse(BaseModel):
    """Enhanced project response for list endpoint with all related data"""
    id: int
    name: str
    description: Optional[str]
    project_type: ProjectType
    industry: Optional[str] = None
    methodology: Optional[str] = None
    project_image_url: Optional[str] = None
    visibility: str = "public"
    owner_id: Optional[int]
    organization_id: Optional[int]
    project_lead_id: Optional[int]
    stacks: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    current_milestone: Optional[str] = "Initial Development"

    # Integration details
    pm_tool: Optional[str]
    vc_tool: Optional[str]
    comm_tool: Optional[str]

    status: Optional[ProjectStatus] = None
    completion_percentage: float = 0.0
    pct_complete: float
    is_visible: bool

    createdAt: datetime
    updatedAt: Optional[datetime] = None

    # Enhanced fields
    members: List[ProjectMemberDetail] = []
    integrated_apps: List[IntegratedAppDetail] = []
    project_lead_name: Optional[str] = None
    organization_name: Optional[str] = None

    model_config = {"from_attributes": True}
