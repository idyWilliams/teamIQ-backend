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


async def fetch_integration_users(provider: str, access_token: str, account_id: str = None, api_key: str = None, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetches available users from the provider.
    If resource_id is provided, fetches users from that specific resource (e.g., repo contributors).
    Returns a standardized list of dicts:
    {
        "id": "user_id",
        "name": "User Name",
        "email": "user@example.com",
        "avatar_url": "...",
        "username": "username"
    }
    """
    if provider == "github":
        return await _fetch_github_users(access_token, resource_id)
    elif provider == "slack":
        return await _fetch_slack_users(access_token, resource_id)
    elif provider == "jira":
        return await _fetch_jira_users(access_token, resource_id)
    elif provider == "gitlab":
        return await _fetch_gitlab_users(access_token, resource_id)
    elif provider == "clickup":
        return await _fetch_clickup_users(api_key, resource_id)
    elif provider == "linear":
        return await _fetch_linear_users(api_key, resource_id)
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


async def _fetch_github_users(token: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch GitHub users.
    If resource_id is provided (format: "owner/repo"), fetch contributors from that repo.
    Otherwise, fetch contributors from all accessible repos.
    """
    async with httpx.AsyncClient() as client:
        all_contributors = {}

        # If resource_id is provided, fetch contributors from that specific repo
        if resource_id:
            # resource_id should be in format "owner/repo" or just repo name
            if "/" in resource_id:
                owner, repo_name = resource_id.split("/", 1)
            else:
                # If only repo name, get authenticated user's username
                user_resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if user_resp.status_code == 200:
                    owner = user_resp.json().get("login")
                    repo_name = resource_id
                else:
                    return []

            # Get contributors for this specific repo
            contrib_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/contributors",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"per_page": 100}
            )

            if contrib_resp.status_code != 200:
                print(f"GitHub contributors error: {contrib_resp.status_code} - {contrib_resp.text}")
                return []

            contributors = contrib_resp.json()

            # For each contributor, get their full profile to fetch email
            for contrib in contributors:
                user_id = str(contrib["id"])

                # Fetch full user profile to get email
                user_resp = await client.get(
                    contrib["url"],
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )

                if user_resp.status_code == 200:
                    user_data = user_resp.json()
                    all_contributors[user_id] = {
                        "id": user_id,
                        "name": user_data.get("name") or user_data.get("login"),
                        "email": user_data.get("email"),
                        "avatar_url": user_data.get("avatar_url"),
                        "username": user_data.get("login")
                    }
        else:
            # Fetch from all accessible repositories (limited to avoid rate limits)
            resp = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"per_page": 100, "affiliation": "owner,collaborator,organization_member"}
            )
            if resp.status_code != 200:
                print(f"GitHub repos error: {resp.status_code} - {resp.text}")
                return []

            repos = resp.json()

            # Fetch contributors from each repository
            for repo in repos[:10]:  # Limit to first 10 repos to avoid rate limiting
                owner = repo["owner"]["login"]
                repo_name = repo["name"]

                # Get contributors for this repo
                contrib_resp = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo_name}/contributors",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"per_page": 100}
                )

                if contrib_resp.status_code != 200:
                    continue

                contributors = contrib_resp.json()

                # For each contributor, get their full profile to fetch email
                for contrib in contributors:
                    user_id = str(contrib["id"])

                    # Skip if we already have this user
                    if user_id in all_contributors:
                        continue

                    # Fetch full user profile to get email
                    user_resp = await client.get(
                        contrib["url"],
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/vnd.github.v3+json"
                        }
                    )

                    if user_resp.status_code == 200:
                        user_data = user_resp.json()
                        all_contributors[user_id] = {
                            "id": user_id,
                            "name": user_data.get("name") or user_data.get("login"),
                            "email": user_data.get("email"),
                            "avatar_url": user_data.get("avatar_url"),
                            "username": user_data.get("login")
                        }

        return list(all_contributors.values())


async def _fetch_slack_users(token: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch Slack users.
    If resource_id is provided (channel ID), fetch members from that channel.
    Otherwise, fetch all workspace members.
    """
    async with httpx.AsyncClient() as client:
        if resource_id:
            # Fetch channel members
            resp = await client.get(
                "https://slack.com/api/conversations.members",
                headers={"Authorization": f"Bearer {token}"},
                params={"channel": resource_id, "limit": 1000}
            )
            data = resp.json()
            if not data.get("ok"):
                print(f"Slack channel members error: {data.get('error')}")
                return []

            member_ids = data.get("members", [])

            # Fetch user info for each member
            users = []
            for user_id in member_ids:
                user_resp = await client.get(
                    "https://slack.com/api/users.info",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"user": user_id}
                )
                user_data = user_resp.json()
                if user_data.get("ok"):
                    u = user_data.get("user", {})
                    if not u.get("deleted") and not u.get("is_bot") and u.get("id") != "USLACKBOT":
                        users.append({
                            "id": u["id"],
                            "name": u.get("real_name") or u.get("name"),
                            "email": u.get("profile", {}).get("email"),
                            "avatar_url": u.get("profile", {}).get("image_48"),
                            "username": u.get("name")
                        })
            return users
        else:
            # Fetch all workspace members
            resp = await client.get(
                "https://slack.com/api/users.list",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 1000}
            )
            data = resp.json()
            if not data.get("ok"):
                print(f"Slack users error: {data.get('error')}")
                return []

            members = data.get("members", [])
            return [
                {
                    "id": m["id"],
                    "name": m.get("real_name") or m.get("name"),
                    "email": m.get("profile", {}).get("email"),
                    "avatar_url": m.get("profile", {}).get("image_48"),
                    "username": m.get("name")
                }
                for m in members
                if not m.get("deleted") and not m.get("is_bot") and m.get("id") != "USLACKBOT"
            ]


async def _fetch_jira_users(token: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch Jira users.
    If resource_id is provided (project ID or key), fetch users assigned to that project.
    Otherwise, fetch all users from the site.
    """
    async with httpx.AsyncClient() as client:
        # Get accessible resources to find site ID
        resp = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code != 200:
            return []

        sites = resp.json()
        if not sites:
            return []

        site_id = sites[0]["id"]

        if resource_id:
            # Fetch users assigned to the specific project
            resp = await client.get(
                f"https://api.atlassian.com/ex/jira/{site_id}/rest/api/3/user/assignable/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"project": resource_id, "maxResults": 100}
            )
        else:
            # Search all users
            resp = await client.get(
                f"https://api.atlassian.com/ex/jira/{site_id}/rest/api/3/users/search",
                headers={"Authorization": f"Bearer {token}"},
                params={"maxResults": 100}
            )

        if resp.status_code != 200:
            print(f"Jira users error: {resp.status_code} - {resp.text}")
            return []

        users = resp.json()
        return [
            {
                "id": u["accountId"],
                "name": u.get("displayName"),
                "email": u.get("emailAddress"), # Often hidden depending on privacy settings
                "avatar_url": u.get("avatarUrls", {}).get("48x48"),
                "username": u.get("displayName")
            }
            for u in users
            if u.get("accountType") == "atlassian"
        ]


async def _fetch_gitlab_users(token: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch GitLab users.
    If resource_id is provided (project ID), fetch members from that project.
    Otherwise, fetch the authenticated user.
    """
    async with httpx.AsyncClient() as client:
        if resource_id:
            # Fetch project members
            resp = await client.get(
                f"https://gitlab.com/api/v4/projects/{resource_id}/members/all",
                headers={"Authorization": f"Bearer {token}"},
                params={"per_page": 100}
            )
            if resp.status_code != 200:
                print(f"GitLab project members error: {resp.status_code} - {resp.text}")
                return []

            members = resp.json()
            return [
                {
                    "id": str(m["id"]),
                    "name": m.get("name"),
                    "email": m.get("email"),  # May be null depending on privacy settings
                    "avatar_url": m.get("avatar_url"),
                    "username": m.get("username")
                }
                for m in members
            ]
        else:
            # Get authenticated user
            resp = await client.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {token}"}
            )
            if resp.status_code != 200:
                return []

            me = resp.json()
            return [{
                "id": str(me["id"]),
                "name": me.get("name"),
                "email": me.get("email"),
                "avatar_url": me.get("avatar_url"),
                "username": me.get("username")
            }]


async def _fetch_clickup_users(api_key: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch ClickUp users.
    If resource_id is provided (list ID), fetch members from that list.
    Otherwise, fetch all team members.
    """
    if not api_key:
        return []
    async with httpx.AsyncClient() as client:
        if resource_id:
            # Fetch list details to get members
            resp = await client.get(
                f"https://api.clickup.com/api/v2/list/{resource_id}",
                headers={"Authorization": api_key}
            )
            if resp.status_code != 200:
                print(f"ClickUp list error: {resp.status_code} - {resp.text}")
                return []

            list_data = resp.json()
            members = list_data.get("members", [])

            return [
                {
                    "id": str(m.get("id")),
                    "name": m.get("username"),
                    "email": m.get("email"),
                    "avatar_url": m.get("profilePicture"),
                    "username": m.get("username")
                }
                for m in members
            ]
        else:
            # Get teams first
            resp = await client.get(
                "https://api.clickup.com/api/v2/team",
                headers={"Authorization": api_key}
            )
            if resp.status_code != 200:
                return []

            teams = resp.json().get("teams", [])
            all_members = []

            for team in teams:
                members = team.get("members", [])
                for m in members:
                    user = m.get("user", {})
                    all_members.append({
                        "id": str(user.get("id")),
                        "name": user.get("username"),
                        "email": user.get("email"),
                        "avatar_url": user.get("profilePicture"),
                        "username": user.get("username")
                    })

            # Deduplicate by ID
            unique_members = {m["id"]: m for m in all_members}.values()
            return list(unique_members)


async def _fetch_linear_users(api_key: str, resource_id: str = None) -> List[Dict[str, Any]]:
    """
    Fetch Linear users.
    If resource_id is provided (team ID), fetch members from that team.
    Otherwise, fetch all workspace users.
    """
    if not api_key:
        return []

    async with httpx.AsyncClient() as client:
        if resource_id:
            # Fetch team members
            query = """
            query($teamId: String!) {
              team(id: $teamId) {
                members {
                  nodes {
                    id
                    name
                    displayName
                    email
                    avatarUrl
                  }
                }
              }
            }
            """
            resp = await client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={"query": query, "variables": {"teamId": resource_id}}
            )
            if resp.status_code != 200:
                print(f"Linear team members error: {resp.status_code} - {resp.text}")
                return []

            data = resp.json()
            members = data.get("data", {}).get("team", {}).get("members", {}).get("nodes", [])

            return [
                {
                    "id": u["id"],
                    "name": u.get("name"),
                    "email": u.get("email"),
                    "avatar_url": u.get("avatarUrl"),
                    "username": u.get("displayName")
                }
                for u in members
            ]
        else:
            # Fetch all workspace users
            query = """
            query {
              users {
                nodes {
                  id
                  name
                  displayName
                  email
                  avatarUrl
                }
              }
            }
            """
            resp = await client.post(
                "https://api.linear.app/graphql",
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={"query": query}
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            users = data.get("data", {}).get("users", {}).get("nodes", [])

            return [
                {
                    "id": u["id"],
                    "name": u.get("name"),
                    "email": u.get("email"),
                    "avatar_url": u.get("avatarUrl"),
                    "username": u.get("displayName")
                }
                for u in users
            ]
