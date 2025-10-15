from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserCreate, OrganizationCreate, Token, PasswordResetRequest, PasswordResetConfirm, UserOut, OrganizationOut, LoginRequest  # Added LoginRequest
from app.repositories import user_repository, organization_repository
from app.core.hashing import verify_password, get_password_hash
from app.core.security import create_access_token, verify_reset_token, create_reset_token, ACCESS_TOKEN_EXPIRE_MINUTES  # For expiry adjust
from app.core.email_utils import send_email
from app.schemas.response_model import create_response
from app.models.user import User
from app.models.organization import Organization
from app.repositories.invitation_repository import get_invitation_by_code, accept_invitation
from typing import Optional
import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register/user")
def register_user(user: UserCreate, db: Session = Depends(get_db), invitation_code: Optional[str] = Query(None)):
    db_user = user_repository.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    organization_id = None
    if invitation_code:
        invitation = get_invitation_by_code(db, invitation_code)
        if invitation:
            organization_id = invitation.organization_id
            accept_invitation(db, invitation_code, None)
    
    new_user = user_repository.create_user(db, user, organization_id=organization_id)
    access_token = create_access_token(data={"sub": new_user.email})
    return create_response(
        success=True,
        message="User registered successfully",
        data=Token(access_token=access_token, token_type="bearer", user=UserOut.model_validate(new_user))
    )

@router.post("/register/organization")
def register_org(org: OrganizationCreate, db: Session = Depends(get_db)):
    if organization_repository.get_organization_by_name(db, org.organization_name):
        raise HTTPException(status_code=400, detail="Organization name already registered")
    
    new_org = organization_repository.create_organization(db, org)
    db.commit()
    db.refresh(new_org)
    
    access_token = create_access_token(data={"sub": new_org.email})
    
    try:
        org_out = OrganizationOut.model_validate(new_org)
    except Exception as e:
        print(f"Validation error: {e}")
        org_out = OrganizationOut.model_validate({**new_org.__dict__, 'social_media_handles': {}, 'favorite_tools': {}})
    
    return create_response(
        success=True,
        message="Organization registered successfully",
        data=Token(access_token=access_token, token_type="bearer", organization=org_out)
    )

@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # Lowercase email for lookup
    login_email = login_data.email.lower()
    
    # Lookup user first, then org
    user_obj = user_repository.get_user_by_email(db, login_email)
    if not user_obj:
        user_obj = organization_repository.get_organization_by_email(db, login_email)
    
    if not user_obj or not verify_password(login_data.password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Adjust expiry for "remember me"
    expires_delta = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if login_data.remember_me:
        expires_delta = datetime.timedelta(days=7)
    
    access_token = create_access_token(data={"sub": user_obj.email}, expires_delta=expires_delta)
    
    # Distinguish user vs org
    if hasattr(user_obj, 'organization_name'):  # Org
        return create_response(
            success=True,
            message="Login successful",
            data=Token(access_token=access_token, token_type="bearer", organization=OrganizationOut.model_validate(user_obj))
        )
    else:  # User/Intern
        return create_response(
            success=True,
            message="Login successful",
            data=Token(access_token=access_token, token_type="bearer", user=UserOut.model_validate(user_obj))
        )

@router.post("/password-reset")
async def request_reset(request: PasswordResetRequest, db: Session = Depends(get_db)):
    # Lowercase email for lookup
    request.email = request.email.lower()
    
    user_obj = user_repository.get_user_by_email(db, request.email) or organization_repository.get_organization_by_email(db, request.email)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    token = create_reset_token(request.email)
    reset_link = f"https://yourapp.com/reset?token={token}"
    await send_email(request.email, reset_link)
    return create_response(success=True, message="Reset email sent")

@router.post("/password-reset/confirm")
def confirm_reset(confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = verify_reset_token(confirm.token)
    user_obj = user_repository.get_user_by_email(db, email) or organization_repository.get_organization_by_email(db, email)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    hashed_pw = get_password_hash(confirm.new_password)
    user_obj.hashed_password = hashed_pw
    db.commit()
    return create_response(success=True, message="Password reset successful")

@router.post("/accept-invitation")
def accept_invite(invitation_code: str, user_id: int, db: Session = Depends(get_db)):
    accept_invitation(db, invitation_code, user_id)
    return create_response(success=True, message="Invitation accepted")