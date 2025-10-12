from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.models.organization import Organization, UserRole
from app.core.database import get_db
from app.core.hashing import get_password_hash
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization

router = APIRouter(prefix="/organizations", tags=["organizations"])

# GET organization by ID
@router.get("/{organization_id}")
def read_organization(organization_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    db_org = db.query(Organization).filter(Organization.id == organization_id).first()
    if db_org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    org_out = OrganizationOut.from_orm(db_org)
    org_out.createdAt = db_org.createdAt
    return create_response(success=True, message="Organization retrieved successfully", data=org_out.model_dump())


# POST register organization
@router.post("/register")
def register_organization(org: OrganizationCreate, db: Session = Depends(get_db)):
    # Check if organization name or email already exists
    existing_org = db.query(Organization).filter(
        (Organization.organization_name == org.organization_name) |
        (Organization.email == org.email)
    ).first()
    if existing_org:
        raise HTTPException(status_code=400, detail="Organization already registered")

    # Hash password
    hashed_pw = get_password_hash(org.password)

    # Create DB object
    db_org = Organization(
        organization_name=org.organization_name,
        team_size=org.team_size,
        email=org.email,
        hashed_password=hashed_pw,
        role="organization"
    )

    db.add(db_org)
    db.commit()
    db.refresh(db_org)

    org_out = OrganizationOut.from_orm(db_org)
    org_out.createdAt = db_org.createdAt
    return create_response(success=True, message="Organization registered successfully", data=org_out.model_dump())
