from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.repositories import organization_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from app.models.organization import Organization

router = APIRouter(tags=["organizations"])

@router.post("/", response_model=OrganizationOut)
def create_org(org: OrganizationCreate, db: Session = Depends(get_db)):
    db_org = organization_repository.create_organization(db, org)
    return create_response(success=True, data=OrganizationOut.from_orm(db_org))

@router.get("/{org_id}", response_model=OrganizationOut)
def get_org(org_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    if not isinstance(current_user, Organization) or current_user.id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db_org = organization_repository.get_organization_by_id(db, org_id)
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return create_response(success=True, data=OrganizationOut.from_orm(db_org))