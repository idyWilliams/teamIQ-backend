from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
# from app.schemas.organization import OrganizationCreate, OrganizationOut, OrganizationSignUp, OrganizationUpdate
from app.schemas.organization import (
    OrganizationSignUp,
    OrganizationOut,
    OrganizationUpdate
)
from app.repositories import organization_repository, user_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from app.models.organization import Organization
from app.core.hashing import get_password_hash
from app.models.organization import UserRole
from app.schemas.response_model import create_response
from app.core.security import create_access_token
from app.core.email_utils import send_organization_signup_email
from app.schemas.auth import Token

router = APIRouter(tags=["organizations"])


@router.post("/signup", status_code=201)
async def signup(
    org: OrganizationSignUp,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # ---------------------------
    # GLOBAL EMAIL VALIDATION
    # Ensure no user or org has same email
    # ---------------------------
    existing_org = organization_repository.get_organization_by_email(db, org.email)
    existing_user = user_repository.get_user_by_email(db, org.email)
    if existing_org or existing_user:
        raise HTTPException(status_code=400, detail="Email already registered in the system")

    # Check for duplicate organization name
    if organization_repository.get_organization_by_name(db, org.organization_name):
        raise HTTPException(status_code=400, detail="Organization name already exists")

    # ---------------------------
    # CREATE ORGANIZATION RECORD
    # ---------------------------
    hashed_password = get_password_hash(org.password)
    new_org = Organization(
        organization_name=org.organization_name,
        team_size=org.team_size,
        email=org.email,
        country=org.country,
        hashed_password=hashed_password,
        role=UserRole.ORGANIZATION
    )

    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    # ---------------------------
    # ISSUE ORGANIZATION TOKEN
    # ---------------------------
    access_token = create_access_token(
        data={"sub": new_org.email, "scope": "organization"}
    )

    # ---------------------------
    # SEND SIGNUP EMAIL ASYNCHRONOUSLY
    # ---------------------------
    background_tasks.add_task(send_organization_signup_email, new_org.email, new_org.organization_name)

    # ---------------------------
    # RETURN TOKEN AND ORG INFO
    # ---------------------------
    org_out = OrganizationOut.model_validate(new_org)
    token_response = Token(
        access_token=access_token,
        token_type="bearer",
        organization=org_out
    )

    return create_response(
        success=True,
        message="Organization signup successful",
        data=token_response
    )





@router.post("/onboardingComplete", response_model=OrganizationOut, status_code=200)
def onboarding_complete(org: OrganizationSignUp, db: Session = Depends(get_db)):
    db_org = organization_repository.get_organization_by_email(db, email=org.email)
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = org.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)

    db.commit()
    db.refresh(db_org)
    return create_response(success=True, message="Organization onboarding completed successfully", data=OrganizationOut.from_orm(db_org))

@router.put("/{org_id}", response_model=OrganizationOut, status_code=200)
def update_org(org_id: int, org_update: OrganizationUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    if not isinstance(current_user, Organization) or current_user.id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db_org = organization_repository.get_organization_by_id(db, org_id)
    if not db_org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = org_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_org, key, value)

    db.commit()
    db.refresh(db_org)
    return create_response(success=True, message="Organization updated successfully", data=OrganizationOut.from_orm(db_org))

@router.get("/{org_id}")
def get_org(org_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user_or_organization)):
    if not isinstance(current_user, Organization) or current_user.id != org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    db_org = organization_repository.get_organization_by_id(db, org_id)
    return create_response(success=True, message="Organization retrieved successfully", data=OrganizationOut.from_orm(db_org))