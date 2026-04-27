# app/api/v1/integrations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.integration import IntegrationCreate, IntegrationResponse, IntegrationTools
from app.repositories.integration_repository import integration_repository
from app.core.database import get_db


router = APIRouter()


@router.get("/tools", response_model=IntegrationTools)
def get_integration_tools():
    """
    Get a list of all available integration tools and their auth methods.
    """
    return {
        "pm": [
            {"name": "jira", "auth_methods": ["api_key"]},
            {"name": "linear", "auth_methods": ["api_key"]},
            {"name": "clickup", "auth_methods": ["api_key"]}
        ],
        "vc": [
            {"name": "github", "auth_methods": ["oauth2", "api_key"]},
            {"name": "gitlab", "auth_methods": ["oauth2", "api_key"]},
            {"name": "bitbucket", "auth_methods": ["oauth2", "api_key"]}
        ],
        "comm": [
            {"name": "slack", "auth_methods": ["api_key", "webhook"]},
            {"name": "discord", "auth_methods": ["api_key", "webhook"]},
            {"name": "teams", "auth_methods": ["oauth2"]}
        ]
    }


@router.post("/", response_model=IntegrationResponse)
def create_integration(
    integration: IntegrationCreate,
    db: Session = Depends(get_db)
):
    return integration_repository.create(db=db, obj_in=integration)

@router.get("/{integration_id}", response_model=IntegrationResponse)
def read_integration(
    integration_id: int,
    db: Session = Depends(get_db)
):
    db_integration = integration_repository.get(db=db, id=integration_id)
    if db_integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return db_integration