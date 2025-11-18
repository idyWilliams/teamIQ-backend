from pydantic import BaseModel
from typing import Optional

# For OrgIntegrationCredential
class OrgIntegrationCredentialIn(BaseModel):
    organization_id: str
    provider: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    api_key: Optional[str] = None

class OrgIntegrationCredentialOut(BaseModel):
    organization_id: str
    provider: str
    client_id: Optional[str]
    api_key: Optional[str]

# For IntegrationConnection
class IntegrationConnectionIn(BaseModel):
    organization_id: str
    provider: str
    account_id: str
    access_token: Optional[str]
    refresh_token: Optional[str]
    api_key: Optional[str]
    connected_by_user_id: str

class IntegrationConnectionOut(BaseModel):
    organization_id: str
    provider: str
    account_id: str
    connected_by_user_id: str
    is_active: bool
