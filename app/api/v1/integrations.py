from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.integration import LinkAccount
from app.repositories import integration_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from typing import List

router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.post("/link")
def link_account(link: LinkAccount, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    account = integration_repository.link_account(db, link, user_id=user_id, org_id=org_id)
    return create_response(success=True, message="Account linked", data=account)

@router.get("/", response_model=List[dict])
def get_linked(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    user_id = current_user.id if hasattr(current_user, 'organization_id') else None
    org_id = current_user.id if not hasattr(current_user, 'organization_id') else None
    accounts = integration_repository.get_linked_accounts(db, user_id=user_id, org_id=org_id)
    return create_response(success=True, data=[{"provider": a.provider, "provider_id": a.provider_id} for a in accounts])