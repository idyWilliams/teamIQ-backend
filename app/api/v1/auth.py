from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status, Request
from sqlalchemy.orm import Session
import datetime
from typing import Optional

from app.core.database import get_db
from app.models.organization import Organization, UserRole
from app.repositories import user_repository, organization_repository
from app.repositories.invitation_repository import get_invitation_by_code
from app.core.hashing import verify_password, get_password_hash
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    create_reset_token,
    get_current_user_or_organization,
    verify_reset_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
# from app.core.email_utils import send_email
from app.core.email_utils import send_password_reset_email
from app.schemas.response_model import create_response
from app.repositories.user_org_repository import link_user_to_org
# Schemas
from app.schemas.user import UserCreate, UserOut
from app.schemas.organization import OrganizationOut
from app.schemas.auth import Token, PasswordResetRequest, PasswordResetConfirm, LoginRequest, RefreshTokenRequest
from app.services.oauth_service import oauth

router = APIRouter()


# ----------------------------
# OAUTH
# ----------------------------

@router.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request, invitation_code: Optional[str] = None):
    """
    Returns the OAuth redirect URL for the specified provider.
    Frontend should redirect the user to this URL.
    """
    client = getattr(oauth, provider, None)
    if not client:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
    
    # Construct redirect URI (frontend callback URL)
    # The frontend will receive the code and send it back to our callback endpoint
    redirect_uri = request.url_for('oauth_callback', provider=provider)
    
    # We can pass invitation_code in the state if needed, or handle it on frontend
    # But usually, it's easier if the frontend handles the redirect and then calls our callback
    # However, if we want to follow Authlib's standard flow:
    state_data = {}
    if invitation_code:
        state_data['invitation_code'] = invitation_code
        
    return await client.authorize_redirect(request, redirect_uri, **state_data)


@router.get("/oauth/{provider}/callback", name="oauth_callback")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """
    Handles the OAuth callback from the provider.
    This endpoint is called by the PROVIDER (or the frontend relaying the code).
    """
    client = getattr(oauth, provider, None)
    if not client:
        raise HTTPException(status_code=400, detail=f"Provider {provider} not supported")
    
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {str(e)}")

    user_info = token.get('userinfo')
    if not user_info:
        # Fallback for providers that don't use OIDC userinfo (like GitHub)
        if provider == 'github':
            resp = await client.get('user', token=token)
            user_info = resp.json()
            # GitHub might not return email in 'user' if it's private
            if not user_info.get('email'):
                emails_resp = await client.get('user/emails', token=token)
                emails = emails_resp.json()
                primary_email = next((e['email'] for e in emails if e['primary']), emails[0]['email'])
                user_info['email'] = primary_email
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from provider")

    email = user_info.get('email').lower()
    first_name = user_info.get('given_name') or user_info.get('name', '').split(' ')[0] or "User"
    last_name = user_info.get('family_name') or (user_info.get('name', '').split(' ')[1] if ' ' in user_info.get('name', '') else "")
    username = user_info.get('preferred_username') or user_info.get('login') or email.split('@')[0]

    # Check if user already exists
    user_entity = user_repository.get_user_by_email(db, email)
    
    is_new_user = False
    entity_type = "user"
    
    if not user_entity:
        # Check if they are an organization (organizations usually login via email/pass)
        org_entity = organization_repository.get_organization_by_email(db, email)
        if org_entity:
            user_entity = org_entity
            entity_type = "organization"
        else:
            # Registration Logic
            invitation_code = request.query_params.get('invitation_code')
            
            # Use random password for OAuth users
            import secrets
            random_pass = secrets.token_urlsafe(32)
            
            user_create = UserCreate(
                email=email,
                first_name=first_name,
                last_name=last_name,
                username=username,
                password=random_pass,
                country="Unknown",
                role=UserRole.INTERN
            )
            
            if invitation_code:
                # Validate invitation
                invitation = get_invitation_by_code(db, invitation_code)
                if not invitation or invitation.is_used:
                     raise HTTPException(status_code=400, detail="Invalid or used invitation code")
                
                user_entity = user_repository.create_user(db, user_create)
                user_entity.auth_provider = provider
                user_entity.auth_id = str(user_info.get('sub') or user_info.get('id'))
                db.flush()
                
                # Link to org
                link_user_to_org(db, user_entity.id, invitation.organization_id)
                
                # Mark invitation used
                invitation.is_used = True
                invitation.accepted = True
                invitation.status = "accepted"
                db.commit()
                is_new_user = True
            else:
                # Sign up without invitation - only if allowed
                # For this app, let's assume registration ALWAYS needs an invite
                # unless we want to allow public signup
                raise HTTPException(status_code=400, detail="User not found. Please use an invitation link to sign up.")
    else:
        # Existing user - update provider info if not set
        if not user_entity.auth_provider or user_entity.auth_provider == 'local':
            user_entity.auth_provider = provider
            user_entity.auth_id = str(user_info.get('sub') or user_info.get('id'))
            db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": email}, entity_type=entity_type)
    refresh_token = create_refresh_token(data={"sub": email}, entity_type=entity_type)

    # Redirect or return JSON?
    # Usually, for callback endpoints called by the provider, we redirect back to frontend with tokens
    from app.core.config import settings
    frontend_url = f"{settings.APP_URL}/oauth-callback?access_token={access_token}&refresh_token={refresh_token}"
    
    # Distinguish if it's a new user for onboarding
    if is_new_user:
        frontend_url += "&new_user=true"
        
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=frontend_url)


@router.post("/register/user")
def register_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    invitation_code: str = Query(..., description="Invitation code is required")
):
    """
    Register a new user with an invitation code.
    Links user to organization via many-to-many relationship.
    """
    # Validate invitation
    invitation = get_invitation_by_code(db, invitation_code)
    if not invitation:
        raise HTTPException(status_code=400, detail="Invalid invitation code")

    if invitation.is_used:
        raise HTTPException(status_code=400, detail="This invitation has already been used")

    if invitation.expires_at < datetime.datetime.now(datetime.timezone.utc):
        # Update status to expired before raising error
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="This invitation has expired. Please request a new invitation.")

    # Prevent registration with organization email
    existing_org = organization_repository.get_organization_by_email(db, user.email)
    if existing_org:
        raise HTTPException(status_code=400, detail="This email is registered to an organization")

    # Check if user already exists
    existing_user = user_repository.get_user_by_email(db, user.email)

    if not existing_user:
        # === NEW USER REGISTRATION ===
        user_entity = user_repository.create_user(
            db=db,
            user=user
            # organization_id removed - not needed for many-to-many
        )

        # Flush to assign ID
        db.flush()

        # Link user to organization via many-to-many
        link_user_to_org(db, user_entity.id, invitation.organization_id)

    else:
        # === EXISTING USER - ADD TO NEW ORGANIZATION ===
        user_entity = existing_user

        # Check if already linked to this organization
        user_orgs = {org.id for org in user_entity.organizations}

        if invitation.organization_id in user_orgs:
            raise HTTPException(
                status_code=400,
                detail="You are already a member of this organization"
            )

        link_user_to_org(db, user_entity.id, invitation.organization_id)

    # ⚠️ UPDATED: Properly mark invitation as accepted
    invitation.is_used = True
    invitation.accepted = True
    invitation.accepted_at = datetime.datetime.now(datetime.timezone.utc)
    invitation.status = "accepted"

    # Commit transaction
    db.commit()
    db.refresh(user_entity)

    # Get user's primary organization (first one they joined)
    primary_org = user_entity.organizations[0] if user_entity.organizations else None

    if not primary_org:
        raise HTTPException(status_code=500, detail="User has no organization")

    organization_out = OrganizationOut.model_validate(primary_org)

    # Generate tokens
    access_token = create_access_token(
        data={"sub": user_entity.email},
        entity_type="user"
    )
    refresh_token = create_refresh_token(
        data={"sub": user_entity.email},
        entity_type="user"
    )

    return create_response(
        success=True,
        message="User registration completed successfully",
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserOut.model_validate(user_entity),
            onboarding_completed=False,
            organization=organization_out,
        )
    )



# ----------------------------
# LOGIN
# ----------------------------
@router.options("/login")
def login_options():
    """Handle CORS preflight for login endpoint"""
    return {"status": "ok"}

@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    # Normalize email
    login_email = login_data.email.lower()

    # Try user -> then organization
    user_obj = user_repository.get_user_by_email(db, login_email)
    entity_type = "user"
    if not user_obj:
        user_obj = organization_repository.get_organization_by_email(db, login_email)
        entity_type = "organization"

    if not user_obj or not verify_password(login_data.password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    # Adjust expiry based on "remember me"
    expires_delta = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if login_data.remember_me:
        expires_delta = datetime.timedelta(days=7)

    access_token = create_access_token(
        data={"sub": user_obj.email},
        expires_delta=expires_delta,
        entity_type=entity_type
    )
    refresh_token = create_refresh_token(
        data={"sub": user_obj.email},
        entity_type=entity_type
    )

    # Distinguish between organization and user
    if entity_type == "organization":  # Organization
        return create_response(
            success=True,
            message="Organization login successful",
            data=Token(
                access_token=access_token, 
                refresh_token=refresh_token,
                token_type="bearer",
                organization=OrganizationOut.model_validate(user_obj),
                onboarding_completed=getattr(user_obj, 'onboarding_completed', False)
            )
        )
    else:  # User
        return create_response(
            success=True,
            message="User login successful",
            data=Token(
                access_token=access_token, 
                refresh_token=refresh_token,
                token_type="bearer",
                user=UserOut.model_validate(user_obj),
                onboarding_completed=getattr(user_obj, 'onboarding_completed', False)
            )
        )


# ----------------------------
# TOKEN REFRESH
# ----------------------------
@router.post("/refresh")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access token.
    """
    payload = decode_token(request.refresh_token)
    
    if not payload or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    entity_type = payload.get("entity_type", "user")
    
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    # Optional: Verify user still exists and is active
    if entity_type == "organization":
        user_obj = organization_repository.get_organization_by_email(db, email)
    else:
        user_obj = user_repository.get_user_by_email(db, email)
        
    if not user_obj:
        raise HTTPException(status_code=401, detail="User not found")

    # Generate new access token
    new_access_token = create_access_token(
        data={"sub": email},
        entity_type=entity_type
    )
    
    # Also generate a new refresh token (refresh token rotation)
    new_refresh_token = create_refresh_token(
        data={"sub": email},
        entity_type=entity_type
    )

    return create_response(
        success=True,
        message="Token refreshed successfully",
        data={
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    )


# ----------------------------
# PASSWORD RESET REQUEST
# ----------------------------
@router.post("/password-reset")
async def request_password_reset(request: PasswordResetRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = request.email.lower()
    user_obj = user_repository.get_user_by_email(db, email) or \
               organization_repository.get_organization_by_email(db, email)

    # Always send same message for privacy
    if not user_obj:
        return create_response(success=True, message="If the email exists, a reset link has been sent")

    token = create_reset_token(email)
    reset_link = f"https://team-iq-frontend.vercel.app/reset-password?token={token}"

    background_tasks.add_task(send_password_reset_email, email, reset_link)


    return create_response(
        success=True,
        message="Reset email sent",
        # data={"reset_link": reset_link}
    )



# ----------------------------
# PASSWORD RESET CONFIRM
# ----------------------------
@router.post("/password-reset/confirm")
def confirm_password_reset(confirm: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Confirm the password reset using a valid token."""
    email = verify_reset_token(confirm.token)

    user_obj = user_repository.get_user_by_email(db, email) or \
               organization_repository.get_organization_by_email(db, email)

    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        hashed_pw = get_password_hash(confirm.new_password)
        user_obj.hashed_password = hashed_pw
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the password. Please try again."
        )

    return create_response(success=True, message="Password reset successful")



@router.post("/logout")
def logout(
    current_user = Depends(get_current_user_or_organization)
):
    """
    Logout endpoint

    In token-based auth, logout is handled client-side by:
    1. Removing token from localStorage/cookies
    2. Optional: Add token to blacklist (implement if needed)

    This endpoint can be used to log the logout event
    """
    from datetime import datetime

    user_type = "organization" if isinstance(current_user, Organization) else "user"
    user_id = current_user.id

    # Log logout event (optional)
    print(f"[LOGOUT] {user_type.upper()} ID {user_id} logged out at {datetime.utcnow()}")

    return create_response(
        success=True,
        message="Logged out successfully. Please remove token from client.",
        data={
            "user_type": user_type,
            "user_id": user_id,
            "logged_out_at": datetime.utcnow().isoformat()
        }
    )
