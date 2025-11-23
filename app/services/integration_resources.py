import httpx
from typing import List, Dict, Any

async def fetch_integration_resources(provider: str, access_token: str, account_id: str = None, api_key: str = None) -> List[Dict[str, Any]]:
    """
    Fetches available resources (repos, channels, projects) from the provider.
    Returns a standardized list of dicts:
    {
        "id": "resource_id",
        "name": "Resource Name",
        "type": "repository|channel|project",
        "metadata": {}
    }
    """
    if provider == "github":
        return await _fetch_github_repos(access_token)
    elif provider == "slack":
        return await _fetch_slack_channels(access_token)
    elif provider == "jira":
        return await _fetch_jira_resources(access_token)
    elif provider == "gitlab":
        return await _fetch_gitlab_projects(access_token)
    elif provider == "clickup":
        return await _fetch_clickup_lists(api_key)
    elif provider == "linear":
        return await _fetch_linear_teams(api_key)
    # Add other providers as needed
    return []

async def _fetch_github_repos(token: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        # Fetch user repos
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            params={"sort": "updated", "per_page": 100}
        )
        if resp.status_code != 200:
            print(f"GitHub Error: {resp.text}")
            return []

        repos = resp.json()
        return [
            {
                "id": str(repo["id"]),
                "name": repo["full_name"],
                "type": "repository",
                "metadata": {
                    "url": repo["html_url"],
                    "description": repo.get("description"),
                    "private": repo.get("private", False)
                }
            }
            for repo in repos
        ]

async def _fetch_slack_channels(token: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {token}"},
            params={"types": "public_channel,private_channel", "limit": 100}
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"Slack Error: {data.get('error')}")
            return []

        channels = data.get("channels", [])
        return [
            {
                "id": channel["id"],
                "name": f"#{channel['name']}",
                "type": "channel",
                "metadata": {
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0)
                }
            }
            for channel in channels
        ]

async def _fetch_jira_resources(token: str) -> List[Dict[str, Any]]:
    # For Jira, we first need the cloud ID (site ID)
    async with httpx.AsyncClient() as client:
        # 1. Get accessible resources (sites)
        resp = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code != 200:
            return []

        sites = resp.json()
        if not sites:
            return []

        # For simplicity, we'll just fetch projects from the first site
        # In a more advanced version, we might return sites as top-level items or iterate all
        site_id = sites[0]["id"]
        site_name = sites[0]["name"]

        # 2. Get projects for this site
        resp = await client.get(
            f"https://api.atlassian.com/ex/jira/{site_id}/rest/api/3/project/search",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        projects = data.get("values", [])

        return [
            {
                "id": proj["id"],
                "name": f"{proj['name']} ({proj['key']})",
                "type": "project",
                "metadata": {
                    "key": proj["key"],
                    "site_name": site_name,
                    "site_id": site_id,
                    "url": proj.get("self") # This is API URL, browser URL would be constructed differently
                }
            }
            for proj in projects
        ]

async def _fetch_gitlab_projects(token: str) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://gitlab.com/api/v4/projects",
            headers={"Authorization": f"Bearer {token}"},
            params={"membership": "true", "simple": "true", "per_page": 100}
        )
        if resp.status_code != 200:
            return []

        projects = resp.json()
        return [
            {
                "id": str(proj["id"]),
                "name": proj["path_with_namespace"],
                "type": "project",
                "metadata": {
                    "url": proj["web_url"],
                    "description": proj.get("description")
                }
            }
            for proj in projects
        ]

async def _fetch_clickup_lists(api_key: str) -> List[Dict[str, Any]]:
    if not api_key:
        return []
    async with httpx.AsyncClient() as client:
        # ClickUp hierarchy is Team -> Space -> Folder -> List
        # This is complex. For MVP, let's just fetch Teams and maybe Spaces?
        # Or just return empty for now if it's too deep.
        # Let's try to fetch Teams first.
        resp = await client.get(
            "https://api.clickup.com/api/v2/team",
            headers={"Authorization": api_key}
        )
        if resp.status_code != 200:
            return []

        teams = resp.json().get("teams", [])
        resources = []

        # For each team, fetch spaces
        for team in teams:
            team_id = team["id"]
            resp_spaces = await client.get(
                f"https://api.clickup.com/api/v2/team/{team_id}/space",
                headers={"Authorization": api_key}
            )
            if resp_spaces.status_code == 200:
                spaces = resp_spaces.json().get("spaces", [])
                for space in spaces:
                    resources.append({
                        "id": space["id"],
                        "name": f"{space['name']} (Space)",
                        "type": "space",
                        "metadata": {
                            "team_name": team["name"]
                        }
                    })
        return resources

async def _fetch_linear_teams(api_key: str) -> List[Dict[str, Any]]:
    if not api_key:
        return []

    query = """
    query {
      teams {
        nodes {
          id
          name
          key
        }
      }
    }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": query}
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        teams = data.get("data", {}).get("teams", {}).get("nodes", [])

        return [
            {
                "id": team["id"],
                "name": f"{team['name']} ({team['key']})",
                "type": "team",
                "metadata": {
                    "key": team["key"]
                }
            }
            for team in teams
        ]
