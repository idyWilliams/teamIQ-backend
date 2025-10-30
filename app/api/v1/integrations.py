# app/api/v1/integrations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.integration import OrganizationIntegration, AuthMethod
from app.schemas.integration import IntegrationCreate, IntegrationResponse
from app.repositories.integration_repository import integration_repository

router = APIRouter()

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