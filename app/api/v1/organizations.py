from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.organization import OrganizationCreate, OrganizationOut
from app.models.organization import Organization
from app.core.database import get_db
from app.core.security import get_password_hash 

router = APIRouter(prefix="/organizations", tags=["organizations"])

# GET organization by ID
@router.get("/{organization_id}", response_model=OrganizationOut)
def read_organization(organization_id: int, db: Session = Depends(get_db)):
    db_org = db.query(Organization).filter(Organization.id == organization_id).first()
    if db_org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return db_org


# POST register organization
@router.post("/register", response_model=OrganizationOut)
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
        hashed_password=hashed_pw
    )

    db.add(db_org)
    db.commit()
    db.refresh(db_org)

    return db_org
