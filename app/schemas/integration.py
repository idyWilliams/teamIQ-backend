from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.integration import AuthMethod, IntegrationType

class IntegrationBase(BaseModel):
    integration_type: str
    integration_name: Optional[str] = None
    auth_method: AuthMethod
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    api_key: Optional[str] = None
    api_token: Optional[str] = None
    base_url: Optional[str] = None
    workspace_id: Optional[str] = None
    workspace_name: Optional[str] = None
    team_id: Optional[str] = None
    config: Optional[dict] = None
    scopes: Optional[list] = None
    is_active: Optional[bool] = True

class IntegrationCreate(IntegrationBase):
    organization_id: int

class IntegrationResponse(IntegrationBase):
    id: int
    organization_id: int
    setup_by_user_id: Optional[int] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True

class LinkAccount(BaseModel):
    provider: str
    provider_id: str
