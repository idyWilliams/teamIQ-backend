from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime


class UserMappingCreate(BaseModel):
    """Schema for creating a user-to-tool account mapping"""
    project_id: int = Field(..., description="ID of the project")
    user_id: int = Field(..., description="ID of the TeamIQ user")
    provider: str = Field(..., description="Provider name (github, slack, jira, etc.)")
    external_user_id: str = Field(..., description="External user ID from the provider")
    external_username: Optional[str] = Field(None, description="External username")
    external_email: Optional[str] = Field(None, description="External email address")


class UserMappingDelete(BaseModel):
    """Schema for deleting a user-to-tool account mapping"""
    project_id: int = Field(..., description="ID of the project")
    user_id: int = Field(..., description="ID of the TeamIQ user")
    provider: str = Field(..., description="Provider name to unmap from")
    reason: Optional[str] = Field(None, description="Optional reason for unmapping")


class UserMappingResponse(BaseModel):
    """Schema for user mapping response"""
    user_id: int
    user_email: str
    user_name: str
    project_id: int
    project_name: str
    mappings: Dict[str, str] = Field(default_factory=dict, description="Provider to external user ID mappings")

    class Config:
        from_attributes = True


class UserMappingDetail(BaseModel):
    """Detailed mapping information for a specific provider"""
    provider: str
    external_user_id: str
    external_username: Optional[str]
    external_email: Optional[str]
    mapped_at: Optional[datetime]


class BulkUserMappingCreate(BaseModel):
    """Schema for bulk mapping multiple users"""
    project_id: int
    mappings: list[UserMappingCreate]
