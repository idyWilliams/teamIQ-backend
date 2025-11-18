from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
from app.core.database import get_db
from app.services.integration import resolve_creds
from app.repositories.integration import upsert_integration_connection
from app.repositories.org_integration_credential import upsert_org_credentials
from app.services.integration_defaults import INTEGRATION_DEFAULTS

router = APIRouter()

# Utility: Provider-specific user info extraction
async def get_account_id_from_provider(provider, access_token, api_key=None):
    """
    Fetches unique external account/user/workspace id for all supported providers.
    """
    async with httpx.AsyncClient() as client:
        if provider == "github":
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id") or user.get("login", "unknown_github_user"))
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
            return user.get("user", {}).get("id", "unknown_slack_user")
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
            return str(user.get("data", {}).get("gid", "unknown_asana_user"))
        elif provider == "notion":
            resp = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Notion-Version": "2022-06-28"
                })
            user = resp.json()
            return str(user.get("id", "unknown_notion_user"))
        elif provider == "teams":
            # Microsoft Graph: /me endpoint
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user.get("id", "unknown_teams_user"))
        # API KEY integrations:
        elif provider == "clickup" and api_key:
            resp = await client.get(
                "https://api.clickup.com/api/v2/user",
                headers={"Authorization": api_key})
            user = resp.json()
            return str(user.get("user", {}).get("id") or user.get("user", {}).get("username", "unknown_clickup_user"))
        elif provider == "trello" and api_key:
            # You need both KEY and a token; funneled from api_key format, e.g. "key:token"
            try:
                key, token = api_key.split(":")
            except Exception:
                return "invalid_trello_key"
            resp = await client.get(
                f"https://api.trello.com/1/members/me?key={key}&token={token}",
            )
            user = resp.json()
            return str(user.get("id", "unknown_trello_member"))
        elif provider == "linear" and api_key:
            resp = await client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={"query": "{ viewer { id name } }"}
            )
            res = resp.json()
            return str(res.get("data", {}).get("viewer", {}).get("id", "unknown_linear_member"))
        else:
            return "external_account_id"

    """Fetches unique external account/user id for supported providers."""
    async with httpx.AsyncClient() as client:
        if provider == "github":
            resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user["id"])
        elif provider == "gitlab":
            resp = await client.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return str(user["id"])
        elif provider == "slack":
            resp = await client.get(
                "https://slack.com/api/users.identity",
                headers={"Authorization": f"Bearer {access_token}"})
            user = resp.json()
            return user.get("user", {}).get("id", "unknown_slack_user")
        elif provider == "jira":
            # Jira returns resources in /accessible-resources; use first site's id
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
        # Add more providers as needed...
        else:
            return "external_account_id"

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
    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        resp = await client.post(creds["token_url"], data=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(400, f"Failed token exchange: {resp.text}")
        token_data = resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "No access token returned")
    # Fetch account info and account_id
    account_id = await get_account_id_from_provider(provider, access_token)
    # Store integration connection for this org/user/provider
    conn = upsert_integration_connection(
        db, {
            "organization_id": orgId,
            "provider": provider,
            "account_id": account_id,
            "access_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "connected_by_user_id": account_id  # improved: set to user_id from your session for real multi-user orgs
        }
    )
    # Redirect to frontend with provider info
    frontend_redirect = f"http://localhost:3000/organization/settings?tab=integrated-apps&connected={provider}"
    return RedirectResponse(frontend_redirect)

@router.post("/save-apikey")
def save_apikey(data: dict = Body(...), db: Session = Depends(get_db)):
    required = ["orgId", "provider", "apiKey"]
    missing = [k for k in required if k not in data]
    if missing:
        raise HTTPException(400, f"Missing keys: {', '.join(missing)}")
    org_id, provider, api_key = data['orgId'], data['provider'], data['apiKey']
    # For API Key integrations, store as org-wide, or specify a user/account if needed.
    record = upsert_org_credentials(db, {
        "organization_id": org_id,
        "provider": provider,
        "api_key": api_key
    })
    # Optionally: validate key (clickup, trello, linear, etc.) here.
    return {"success": True, "provider": provider}
