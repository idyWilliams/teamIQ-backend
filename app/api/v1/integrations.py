# app/api/v1/integrations.py

from fastapi import APIRouter, Depends, Body, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
import os
import httpx

from app.core.database import get_db
from app.services.integration_defaults import INTEGRATION_DEFAULTS
from app.models.integration import IntegrationConnection
from app.models.org_integration_credential import OrgIntegrationCredential
from app.repositories.integration import upsert_integration_connection
from app.repositories.org_integration_credential import get_org_credentials, upsert_org_credentials


router = APIRouter()

# --------- Credential Logic ---------
def resolve_creds(db, org_id, provider):
    """
    Resolves client id, client secret, redirect_uri, scopes etc.
    Uses org-specific credentials if present, defaults otherwise.
    """
    defaults = INTEGRATION_DEFAULTS.get(provider)
    if not defaults:
        raise HTTPException(400, f"Provider {provider} is not supported.")
    env_id = os.getenv(defaults.get("client_id_env", ""), "")
    env_secret = os.getenv(defaults.get("client_secret_env", ""), "")
    env_redirect = os.getenv(defaults.get("redirect_uri_env", ""), "")
    org_cred = get_org_credentials(db, org_id, provider)
    return {
        "client_id": org_cred.client_id if org_cred and org_cred.client_id else env_id,
        "client_secret": org_cred.client_secret if org_cred and org_cred.client_secret else env_secret,
        "redirect_uri": env_redirect,
        "scopes": defaults.get("scopes", ""),
        "authorize_url": defaults.get("authorize_url", ""),
        "token_url": defaults.get("token_url", ""),
        "type": defaults.get("type", ""),
        "api_key": org_cred.api_key if org_cred and org_cred.api_key else None,
    }

# --------- Third-party Account Identifier Logic ---------
async def get_account_id_from_provider(provider, access_token, api_key=None):
    """
    Gets a unique account/workspace ID from external provider for proper linkage.
    """
    async with httpx.AsyncClient() as client:
        if provider == "github":
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id") or user.get("login", "github_user"))
        elif provider == "gitlab":
            resp = await client.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id"))
        elif provider == "slack":
            resp = await client.get(
                "https://slack.com/api/users.identity",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return user.get("user", {}).get("id", "slack_user")
        elif provider == "jira":
            resp = await client.get(
                "https://api.atlassian.com/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            res = resp.json()
            if isinstance(res, list) and res:
                return res[0].get("id", "jira_site")
            return "jira_site"
        elif provider == "discord":
            resp = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id"))
        elif provider == "figma":
            resp = await client.get(
                "https://api.figma.com/v1/me",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id"))
        elif provider == "asana":
            resp = await client.get(
                "https://app.asana.com/api/1.0/users/me",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("data", {}).get("gid", "asana_user"))
        elif provider == "notion":
            resp = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": "2022-06-28"
                })
            user = resp.json()
            return str(user.get("id", "notion_user"))
        elif provider == "teams":
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id", "teams_user"))
        elif provider == "clickup" and api_key:
            resp = await client.get(
                "https://api.clickup.com/api/v2/user",
                headers={"Authorization": api_key})
            user = resp.json()
            return str(user.get("user", {}).get("id") or user.get("user", {}).get("username", "clickup_user"))
        elif provider == "trello" and api_key:
            try:
                key, token = api_key.split(":")
            except Exception:
                return "invalid_trello_key"
            resp = await client.get(
                f"https://api.trello.com/1/members/me?key={key}&token={token}",
            )
            user = resp.json()
            return str(user.get("id", "trello_member"))
        elif provider == "linear" and api_key:
            resp = await client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={"query": "{ viewer { id name } }"}
            )
            res = resp.json()
            return str(res.get("data", {}).get("viewer", {}).get("id", "linear_member"))
        else:
            return f"{provider}_account"

# --------- Core Integration CRUD/API ---------
@router.get("/")
def list_integrations(org_id: str = Query(...), db: Session = Depends(get_db)):
    conns = db.query(IntegrationConnection).filter_by(
        organization_id=org_id, is_active=True
    ).all()
    return [
        {
            "id": c.id,
            "organization_id": c.organization_id,
            "provider": c.provider,
            "account_id": c.account_id,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "updated_at": c.updated_at.isoformat() if c.updated_at else "",
        }
        for c in conns
    ]

@router.delete("/{connection_id}")
def remove_integration(connection_id: int, db: Session = Depends(get_db)):
    conn = db.query(IntegrationConnection).filter_by(id=connection_id, is_active=True).first()
    if not conn:
        raise HTTPException(404, detail="Integration not found")
    conn.is_active = False
    db.commit()
    return {"success": True, "id": connection_id}

@router.post("/{connection_id}/sync")
def sync_integration(connection_id: int, db: Session = Depends(get_db)):
    conn = db.query(IntegrationConnection).filter_by(id=connection_id, is_active=True).first()
    if not conn:
        raise HTTPException(404, detail="Integration not found")
    conn.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "synced_at": conn.updated_at.isoformat()}

# --------- OAuth & Key Flows ---------
@router.get("/oauth/start")
def oauth_start(provider: str, orgId: str, db: Session = Depends(get_db)):
    creds = resolve_creds(db, orgId, provider)
    state = f"{orgId}:{provider}"
    params = {
        "client_id": creds["client_id"],
        "redirect_uri": creds["redirect_uri"],
        "scope": creds["scopes"],
        "state": state,
        "response_type": "code",
    }
    # Use urlencode for proper escaping
    from urllib.parse import urlencode
    url = f"{creds['authorize_url']}?{urlencode(params)}"
    return RedirectResponse(url)

@router.get("/oauth/callback")
async def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        orgId, provider = state.split(":")
    except Exception:
        raise HTTPException(400, "Invalid state param structure")
    creds = resolve_creds(db, orgId, provider)
    payload = {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "code": code,
        "redirect_uri": creds["redirect_uri"],
        "grant_type": "authorization_code"
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(creds["token_url"], data=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(400, f"Failed token exchange: {resp.text}")
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "No access token returned")
    account_id = await get_account_id_from_provider(provider, access_token)
    upsert_integration_connection(
        db, {
            "organization_id": orgId,
            "provider": provider,
            "account_id": account_id,
            "access_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "connected_by_user_id": account_id
        }
    )
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3001")
    # Redirect to frontend callback page which will show success animation
    frontend_redirect = f"{frontend_url}/auth/callback/{provider}?success=true"
    return RedirectResponse(frontend_redirect)

@router.post("/save-apikey")
async def save_apikey(data: dict = Body(...), db: Session = Depends(get_db)):
    required = ["orgId", "provider", "apiKey"]
    missing = [k for k in required if k not in data]
    if missing:
        raise HTTPException(400, f"Missing keys: {', '.join(missing)}")
    org_id, provider, api_key = data['orgId'], data['provider'], data['apiKey']
    # Optionally: validate the key with provider
    account_id = await get_account_id_from_provider(provider, None, api_key=api_key)
    upsert_org_credentials(db, {
        "organization_id": org_id,
        "provider": provider,
        "api_key": api_key
    })
    upsert_integration_connection(
        db, {
            "organization_id": org_id,
            "provider": provider,
            "account_id": account_id,
            "api_key": api_key,
            "connected_by_user_id": account_id
        }
    )
    return {"success": True, "provider": provider, "account_id": account_id}

# --------- Provider (BYOC) Credentials CRUD (Enterprise) ---------
@router.get("/provider-credentials")
def get_provider_credentials(
    orgId: str = Query(...), provider: str = Query(...),
    db: Session = Depends(get_db)
):
    cred = db.query(OrgIntegrationCredential).filter_by(
        organization_id=orgId, provider=provider
    ).first()
    if not cred:
        return {}
    return {
        "organization_id": cred.organization_id,
        "provider": cred.provider,
        "client_id": cred.client_id,
        "client_secret": None  # Never return the actual secret
    }

@router.post("/provider-credentials")
def set_provider_credentials(
    data: dict = Body(...), db: Session = Depends(get_db)
):
    org_id = data.get("organization_id")
    provider = data.get("provider")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")
    if not (org_id and provider and client_id and client_secret):
        raise HTTPException(400, "Missing required fields")
    cred = db.query(OrgIntegrationCredential).filter_by(
        organization_id=org_id, provider=provider
    ).first()
    if cred:
        cred.client_id = client_id
        cred.client_secret = client_secret
    else:
        cred = OrgIntegrationCredential(
            organization_id=org_id, provider=provider,
            client_id=client_id, client_secret=client_secret
        )
        db.add(cred)
    db.commit()
    db.refresh(cred)
    return {
        "organization_id": cred.organization_id,
        "provider": cred.provider,
        "client_id": cred.client_id,
        "client_secret": None
    }
