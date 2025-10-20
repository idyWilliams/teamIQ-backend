import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DataError
from fastapi import HTTPException, status
from app.models.organization import Organization, UserRole
from app.schemas.organization import OrganizationCreate  # Fixed import
from app.core.hashing import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_organization_by_name(db: Session, name: str):
    logger.info(f"Using UserRole enum: {[(e.name, e.value) for e in UserRole]}")
    result = db.query(Organization).filter(Organization.organization_name == name).first()
    logger.info(f"Queried organization: {name}, role: {result.role if result else None}")
    return result

def get_organization_by_email(db: Session, email: str):
    return db.query(Organization).filter(Organization.email == email.lower()).first()  # Fixed: Lowercase for case-insensitivity

def get_organization_by_id(db: Session, org_id: int):
    return db.query(Organization).filter(Organization.id == org_id).first()

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
        email=organization.email.lower(),  # Fixed: Store lowercase
        hashed_password=hashed_pw,
        role=UserRole.ORGANIZATION,
        organization_image=organization.organization_image,
        description=organization.description,
        sector=organization.sector,
        social_media_handles=organization.social_media_handles,  # Assumes dict; SQLAlchemy handles JSON
        domain_link=organization.domain_link,
        favorite_tools=organization.favorite_tools,
        website=organization.website,
        address=organization.address,
        phone_number=organization.phone_number
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    return new_org