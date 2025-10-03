import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from fastapi import HTTPException, status
from app.models.organization import Organization, UserRole
from app.schemas.organization import OrganizationCreate
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_organization_by_name(db: Session, name: str):
    try:
        logger.info(f"Using UserRole enum: {[(e.name, e.value) for e in UserRole]}")
        result = db.query(Organization).filter(Organization.organization_name == name).first()
        logger.info(f"Queried organization: {name}, role: {result.role if result else None}")
        return result
    except DataError as e:
        logger.error(f"Enum value error for organization {name}: {e}")
        raise HTTPException(status_code=500, detail="Invalid role value in database")

def get_organization_by_email(db: Session, email: str):
    return db.query(Organization).filter(Organization.email == email).first()

def create_organization(db: Session, organization: OrganizationCreate):
    if get_organization_by_name(db, organization.organization_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization already registered"
        )
    hashed_pw = get_password_hash(organization.password)
    new_org = Organization(
        organization_name=organization.organization_name,
        team_size=organization.team_size,
        email=organization.email,
        hashed_password=hashed_pw,
        role=UserRole.ORGANIZATION.value  # Use .value to ensure 'organization' (lowercase)
    )
    try:
        db.add(new_org)
        db.commit()
        db.refresh(new_org)
        return new_org
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Organization could not be created")
    except DataError as e:
        db.rollback()
        logger.error(f"DataError in create_organization: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")