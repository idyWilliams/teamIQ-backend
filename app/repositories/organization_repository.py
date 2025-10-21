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
