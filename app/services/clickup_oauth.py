"""
ClickUp OAuth API helpers.

Provides functions to:
- Get ClickUp access token for an organization
- Make authenticated ClickUp API calls

Supports both OAuth and API-key authentication methods.
"""

import httpx
from sqlalchemy.orm import Session
from app.models.integration import IntegrationConnection
from app.repositories.integration import get_slack_bot_token


def get_clickup_access_token(db: Session, org_id: str) -> str | None:
    """
    Get ClickUp access token for an organization.

    Prefers OAuth token if available, falls back to API key.
    Returns None if no ClickUp integration is active.
    """
    conn = db.query(IntegrationConnection).filter_by(
        organization_id=org_id,
        provider="clickup",
        is_active=True
    ).first()

    if not conn:
        return None

    # OAuth token takes precedence
    if conn.access_token:
        return conn.access_token

    # Fall back to API key
    return conn.api_key


def get_clickup_connection(db: Session, org_id: str) -> IntegrationConnection | None:
    """
    Get the full ClickUp integration connection for an organization.
    Useful when you need access_token, refresh_token, account_id, etc.
    """
    return db.query(IntegrationConnection).filter_by(
        organization_id=org_id,
        provider="clickup",
        is_active=True
    ).first()


async def call_clickup_api(
    db: Session,
    org_id: str,
    endpoint: str,
    method: str = "GET",
    json_data: dict | None = None,
    params: dict | None = None
) -> dict:
    """
    Make an authenticated request to ClickUp API.

    Args:
        db: Database session
        org_id: Organization ID
        endpoint: API endpoint (e.g., "/user", "/team", "/space/{space_id}")
        method: HTTP method (GET, POST, PUT, DELETE)
        json_data: JSON body for POST/PUT requests
        params: Query parameters

    Returns:
        Parsed JSON response

    Raises:
        HTTPError: If API call fails
        ValueError: If no ClickUp integration found
    """
    token = get_clickup_access_token(db, org_id)

    if not token:
        raise ValueError(f"No ClickUp integration found for organization {org_id}")

    # Determine auth header based on token type
    # OAuth tokens use Bearer, API keys use the key directly
    conn = get_clickup_connection(db, org_id)
    if conn and conn.access_token:
        auth_header = f"Bearer {token}"
    else:
        auth_header = token

    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }

    url = f"https://api.clickup.com/api/v2{endpoint}"

    async with httpx.AsyncClient() as client:
        if method == "GET":
            resp = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=json_data, params=params)
        elif method == "PUT":
            resp = await client.put(url, headers=headers, json=json_data, params=params)
        elif method == "DELETE":
            resp = await client.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        resp.raise_for_status()
        return resp.json()


# Convenience methods for common ClickUp API operations

async def get_clickup_user(db: Session, org_id: str) -> dict:
    """Get current authenticated user info."""
    return await call_clickup_api(db, org_id, "/user")


async def get_clickup_teams(db: Session, org_id: str) -> list:
    """Get all teams/workspaces accessible to this integration."""
    result = await call_clickup_api(db, org_id, "/team")
    return result.get("teams", [])


async def get_clickup_spaces(db: Session, org_id: str, team_id: str) -> list:
    """Get all spaces in a team."""
    result = await call_clickup_api(db, org_id, f"/team/{team_id}/space")
    return result.get("spaces", [])


async def get_clickup_lists(db: Session, org_id: str, space_id: str) -> list:
    """Get all lists in a space."""
    result = await call_clickup_api(db, org_id, f"/space/{space_id}/list")
    return result.get("lists", [])


async def get_clickup_tasks(
    db: Session,
    org_id: str,
    list_id: str,
    include_closed: bool = False
) -> list:
    """Get tasks from a list."""
    params = {"include_closed": "true"} if include_closed else {}
    result = await call_clickup_api(db, org_id, f"/list/{list_id}/task", params=params)
    return result.get("tasks", [])


async def get_clickup_task(db: Session, org_id: str, task_id: str) -> dict:
    """Get a specific task by ID."""
    return await call_clickup_api(db, org_id, f"/task/{task_id}")


async def create_clickup_task(
    db: Session,
    org_id: str,
    list_id: str,
    name: str,
    description: str = "",
    status: str = "to do"
) -> dict:
    """Create a new task in a list."""
    task_data = {
        "name": name,
        "description": description,
        "status": status
    }
    return await call_clickup_api(
        db, org_id, f"/list/{list_id}/task",
        method="POST",
        json_data=task_data
    )


async def update_clickup_task(
    db: Session,
    org_id: str,
    task_id: str,
    **updates
) -> dict:
    """Update an existing task."""
    return await call_clickup_api(
        db, org_id, f"/task/{task_id}",
        method="PUT",
        json_data=updates
    )


async def delete_clickup_task(db: Session, org_id: str, task_id: str) -> None:
    """Delete a task."""
    await call_clickup_api(
        db, org_id, f"/task/{task_id}",
        method="DELETE"
    )
