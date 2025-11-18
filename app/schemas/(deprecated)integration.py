from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.integration import AuthMethod

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

    class Config:
        from_attributes = True


class IntegrationTools(BaseModel):
    pm: list["IntegrationToolDetail"]
    vc: list["IntegrationToolDetail"]
    comm: list["IntegrationToolDetail"]


class IntegrationToolDetail(BaseModel):
    name: str
    auth_methods: list[str]


class LinkAccount(BaseModel):
    provider: str
    provider_id: str
