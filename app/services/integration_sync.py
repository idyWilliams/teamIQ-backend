"""
Integration Sync Service
Handles syncing data from external tools (Jira, GitHub, Slack, etc.) to local database
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
from app.models.project import Project, IntegrationMethod
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.organization import Organization
from app.models.contribution import Contribution
from app.models.activity import Activity


class IntegrationError(Exception):
    """Custom exception for integration errors"""
    pass


class BaseIntegrationSync:
    """Base class for all integration syncs"""

    def __init__(self, project: Project, db: Session):
        self.project = project
        self.db = db
        self.organization = db.query(Organization).filter(
            Organization.id == project.organization_id
        ).first()

    def is_configured(self) -> bool:
        """Check if integration is properly configured"""
        raise NotImplementedError

    def _store_integration_error(self, error_message: str):
        """Store integration error for user notification"""
        print(f"📝 Integration error for project {self.project.id}: {error_message}")
        # TODO: Store in database for user dashboard notifications

    def _get_user_from_external_id(self, provider: str, external_id: str) -> Optional[int]:
        """
        Get TeamIQ user_id from external platform user ID using mappings.
        Falls back to email matching if no mapping exists.

        Args:
            provider: Platform name (e.g., 'github', 'slack', 'jira')
            external_id: User ID on the external platform

        Returns:
            TeamIQ user_id or None if not found
        """
        from app.models.project import ProjectMember
        from sqlalchemy import cast, String
        from sqlalchemy.dialects.postgresql import JSONB

        if not external_id:
            return None

        # Try to find user via external_mappings
        member = self.db.query(ProjectMember).filter(
            ProjectMember.project_id == self.project.id,
            cast(ProjectMember.external_mappings[provider], String) == str(external_id)
        ).first()

        if member:
            return member.user_id

        # No mapping found
        print(f"⚠️  No mapping found for {provider} user {external_id} in project {self.project.id}")
        return None


# ============================================================================
# PROJECT MANAGEMENT TOOLS SYNC (Jira, Linear, ClickUp)
# ============================================================================

class PMToolSync(BaseIntegrationSync):
    """Sync for Project Management Tools (Jira, Linear, ClickUp)"""

    def is_configured(self) -> bool:
        """Check if any PM resources are linked"""
        # Check if there are any resources associated with PM tools
        pm_providers = ["jira", "linear", "clickup"]
        return any(
            r.connection.provider in pm_providers
            for r in self.project.resources
        )

    def get_headers(self) -> Dict:
        """Build auth headers based on integration method"""
        if self.project.pm_integration_method == IntegrationMethod.OAUTH2:
            return {"Authorization": f"Bearer {self.project.pm_access_token}"}
        elif self.project.pm_integration_method == IntegrationMethod.API_KEY:
            if self.project.pm_tool == "jira":
                return {"Authorization": f"Bearer {self.project.pm_api_key}"}
            elif self.project.pm_tool == "linear":
                return {"Authorization": self.project.pm_api_key}
            elif self.project.pm_tool == "clickup":
                return {"Authorization": self.project.pm_api_key}
        return {}

    def get_jira_workspace_url(self) -> str:
        """Get Jira workspace URL from project configuration"""
        if not self.project.pm_workspace_url:
            raise IntegrationError(
                "Jira workspace URL is not configured. "
                "Please provide your Jira workspace URL in Step 2 of project setup "
                "(e.g., yourcompany.atlassian.net)"
            )

        workspace = self.project.pm_workspace_url.strip()
        workspace = workspace.replace("https://", "").replace("http://", "")
        workspace = workspace.rstrip("/")

        if not (".atlassian.net" in workspace or "jira" in workspace.lower()):
            raise IntegrationError(
                f"Invalid Jira workspace URL: {workspace}. "
                "Expected format: yourcompany.atlassian.net"
            )

        return workspace

    def get_api_url(self) -> Optional[str]:
        """Build API URL based on tool and project configuration"""
        if self.project.pm_tool == "jira":
            workspace = self.get_jira_workspace_url()
            return f"https://{workspace}/rest/api/3"

        elif self.project.pm_tool == "linear":
            return "https://api.linear.app/graphql"

        elif self.project.pm_tool == "clickup":
            if not self.project.pm_project_id:
                raise IntegrationError("ClickUp list ID is required")
            return f"https://api.clickup.com/api/v2/list/{self.project.pm_project_id}/task"

        return None

    def sync_tasks(self):
        """Sync tasks from all linked PM resources"""
        if not self.is_configured():
            print(f"⚠️  No PM resources linked for project {self.project.id}")
            return

        for resource in self.project.resources:
            try:
                provider = resource.connection.provider
                if provider == "jira":
                    self._sync_jira_issues(resource)
                elif provider == "linear":
                    self._sync_linear_issues(resource)
                elif provider == "clickup":
                    self._sync_clickup_tasks(resource)

            except IntegrationError as e:
                print(f"❌ Integration Error ({provider}): {str(e)}")
                self._store_integration_error(str(e))

            except Exception as e:
                print(f"❌ Unexpected error ({provider}): {str(e)}")
                self._store_integration_error(f"Sync failed: {str(e)}")

    def _sync_jira_issues(self, resource):
        """Fetch and sync Jira issues for a specific resource"""
        # resource.resource_id is the Jira Project Key or ID
        # resource.metadata contains site_id, url, etc.

        token = resource.connection.access_token
        site_id = resource.metadata.get("site_id")

        if not token or not site_id:
            raise IntegrationError("Missing Jira credentials or site ID")

        api_url = f"https://api.atlassian.com/ex/jira/{site_id}/rest/api/3"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(
                f"{api_url}/search",
                headers=headers,
                params={
                    "jql": f"project={resource.resource_id}", # resource_id is the Project ID/Key
                    "maxResults": 100,
                    "fields": "summary,description,status,assignee,duedate"
                },
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("Jira authentication failed.")

            if response.status_code != 200:
                raise IntegrationError(f"Jira API error: {response.status_code} - {response.text}")

            issues = response.json().get("issues", [])
            # Pass site_id or constructed URL base for linking
            # Construct workspace URL from metadata if available, or just use site_id for now
            workspace_url = resource.metadata.get("url", "")
            self._save_tasks_to_db(issues, "jira", workspace_url)
            print(f"✅ Synced {len(issues)} Jira issues from {resource.resource_name}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Jira: {str(e)}")

    def _sync_linear_issues(self, resource):
        """Fetch and sync Linear issues"""
        api_key = resource.connection.api_key
        if not api_key:
             raise IntegrationError("Missing Linear API key")

        headers = {"Authorization": api_key, "Content-Type": "application/json"}

        # resource.resource_id should be the Team ID
        team_id = resource.resource_id

        query = """
        query($teamId: String!) {
            issues(filter: {team: {id: {eq: $teamId}}}) {
                nodes {
                    id
                    title
                    description
                    state { name }
                    assignee { email }
                    dueDate
                    url
                }
            }
        }
        """

        try:
            response = requests.post(
                "https://api.linear.app/graphql",
                headers=headers,
                json={
                    "query": query,
                    "variables": {"teamId": team_id}
                },
                timeout=30
            )

            if response.status_code != 200:
                raise IntegrationError(f"Linear API error: {response.status_code}")

            data = response.json()
            if "errors" in data:
                raise IntegrationError(f"Linear API error: {data['errors'][0]['message']}")

            issues = data.get("data", {}).get("issues", {}).get("nodes", [])
            self._save_tasks_to_db(issues, "linear")
            print(f"✅ Synced {len(issues)} Linear issues from {resource.resource_name}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Linear: {str(e)}")

    def _sync_clickup_tasks(self, resource):
        """Fetch and sync ClickUp tasks - supports both OAuth and API key"""
        # OAuth token takes precedence over API key
        auth_token = resource.connection.access_token or resource.connection.api_key
        if not auth_token:
            raise IntegrationError("Missing ClickUp credentials")

        # Determine auth header based on token type
        if resource.connection.access_token:
            headers = {"Authorization": f"Bearer {auth_token}"}
        else:
            headers = {"Authorization": auth_token}

        list_id = resource.resource_id

        try:
            response = requests.get(
                f"https://api.clickup.com/api/v2/list/{list_id}/task",
                headers=headers,
                timeout=30
            )

            if response.status_code != 200:
                raise IntegrationError(f"ClickUp API error: {response.status_code}")

            tasks = response.json().get("tasks", [])
            self._save_tasks_to_db(tasks, "clickup")
            print(f"✅ Synced {len(tasks)} ClickUp tasks from {resource.resource_name}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to ClickUp: {str(e)}")

    def _save_tasks_to_db(self, external_tasks: List[Dict], source: str, workspace: str = None):
        """Save/update tasks in database"""
        for ext_task in external_tasks:
            try:
                if source == "jira":
                    task_id = ext_task["id"]
                    title = ext_task["fields"]["summary"]
                    description = ext_task["fields"].get("description")
                    status_name = ext_task["fields"]["status"]["name"]
                    # Get Jira account ID instead of email
                    assignee_data = ext_task["fields"].get("assignee", {})
                    assignee_external_id = assignee_data.get("accountId") if assignee_data else None
                    due_date = ext_task["fields"].get("duedate")
                    url = f"https://{workspace}/browse/{ext_task['key']}"

                elif source == "linear":
                    task_id = ext_task["id"]
                    title = ext_task["title"]
                    description = ext_task.get("description")
                    status_name = ext_task["state"]["name"]
                    # Linear uses ID for assignee
                    assignee_data = ext_task.get("assignee", {})
                    assignee_external_id = assignee_data.get("id") if assignee_data else None
                    due_date = ext_task.get("dueDate")
                    url = ext_task["url"]

                elif source == "clickup":
                    task_id = ext_task["id"]
                    title = ext_task["name"]
                    description = ext_task.get("description")
                    status_name = ext_task["status"]["status"]
                    assignees = ext_task.get("assignees", [])
                    # ClickUp uses numeric ID for assignee
                    assignee_external_id = str(assignees[0].get("id")) if assignees else None
                    due_date = ext_task.get("due_date")
                    url = ext_task["url"]

                # Find or create task
                task = self.db.query(Task).filter(
                    Task.external_id == task_id,
                    Task.external_source == source
                ).first()

                if not task:
                    task = Task(
                        external_id=task_id,
                        external_source=source,
                        external_url=url,
                        organization_id=self.project.organization_id,
                        project_id=self.project.id
                    )
                    self.db.add(task)

                # Update task fields
                task.title = title
                task.description = description
                task.status = self._map_status(status_name, source)
                task.due_date = due_date
                task.external_url = url

                # Map assignee using external_mappings
                if assignee_external_id:
                    user_id = self._get_user_from_external_id(source, assignee_external_id)
                    if user_id:
                        task.owner_id = user_id
                    else:
                        print(f"⚠️  Task '{title}' assigned to unmapped {source} user {assignee_external_id}")

            except Exception as e:
                print(f"⚠️  Error processing task: {str(e)}")
                continue

        self.db.commit()

    def _map_status(self, external_status: str, source: str) -> TaskStatus:
        """Map external status to TaskStatus enum"""
        status_maps = {
            "jira": {
                "to do": TaskStatus.TODO,
                "in progress": TaskStatus.IN_PROGRESS,
                "done": TaskStatus.DONE,
            },
            "linear": {
                "todo": TaskStatus.TODO,
                "in progress": TaskStatus.IN_PROGRESS,
                "done": TaskStatus.DONE,
                "completed": TaskStatus.DONE,
            },
            "clickup": {
                "to do": TaskStatus.TODO,
                "in progress": TaskStatus.IN_PROGRESS,
                "complete": TaskStatus.DONE,
            }
        }

        status_map = status_maps.get(source, {})
        return status_map.get(external_status.lower(), TaskStatus.TODO)


# ============================================================================
# VERSION CONTROL SYNC (GitHub, GitLab, Bitbucket)
# ============================================================================

class VersionControlSync(BaseIntegrationSync):
    """Sync for Version Control (GitHub, GitLab, Bitbucket)"""

    def is_configured(self) -> bool:
        """Check if any VC resources are linked"""
        vc_providers = ["github", "gitlab", "bitbucket"]
        return any(
            r.connection.provider in vc_providers
            for r in self.project.resources
        )

    def get_headers(self) -> Dict:
        """Build auth headers based on VC tool"""
        if self.project.vc_integration_method == IntegrationMethod.OAUTH2:
            if self.project.vc_tool == "github":
                return {"Authorization": f"Bearer {self.project.vc_access_token}"}
            elif self.project.vc_tool == "gitlab":
                return {"Authorization": f"Bearer {self.project.vc_access_token}"}
            elif self.project.vc_tool == "bitbucket":
                return {"Authorization": f"Bearer {self.project.vc_access_token}"}

        elif self.project.vc_integration_method == IntegrationMethod.API_KEY:
            if self.project.vc_tool == "github":
                return {"Authorization": f"token {self.project.vc_api_key}"}
            elif self.project.vc_tool == "gitlab":
                return {"PRIVATE-TOKEN": self.project.vc_api_key}
            elif self.project.vc_tool == "bitbucket":
                return {"Authorization": f"Bearer {self.project.vc_api_key}"}

        return {}

    def get_repo_path(self) -> Optional[str]:
        """Extract repo path from repository URL"""
        url = self.project.vc_repository_url

        if "github.com" in url:
            return url.replace("https://github.com/", "").replace(".git", "")
        elif "gitlab.com" in url:
            return url.replace("https://gitlab.com/", "").replace(".git", "")
        elif "bitbucket.org" in url:
            return url.replace("https://bitbucket.org/", "").replace(".git", "")

        return None

    def sync_commits(self):
        """Sync recent commits from all linked VC resources"""
        if not self.is_configured():
            print(f"⚠️  No VC resources linked for project {self.project.id}")
            return

        for resource in self.project.resources:
            try:
                provider = resource.connection.provider
                if provider == "github":
                    self._sync_github_commits(resource)
                elif provider == "gitlab":
                    self._sync_gitlab_commits(resource)
                elif provider == "bitbucket":
                    self._sync_bitbucket_commits(resource)

            except IntegrationError as e:
                print(f"❌ VC Integration Error ({provider}): {str(e)}")
                self._store_integration_error(str(e))

            except Exception as e:
                print(f"❌ Unexpected VC error ({provider}): {str(e)}")
                self._store_integration_error(f"VC sync failed: {str(e)}")

    def _sync_github_commits(self, resource):
        """Fetch commits from GitHub"""
        # resource.name is typically "owner/repo"
        repo_path = resource.name
        token = resource.connection.access_token

        if not token:
            raise IntegrationError("Missing GitHub access token")

        headers = {"Authorization": f"Bearer {token}"}
        since = datetime.utcnow() - timedelta(days=30)

        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo_path}/commits",
                headers=headers,
                params={"since": since.isoformat(), "per_page": 100},
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("GitHub authentication failed.")

            if response.status_code == 404:
                raise IntegrationError(f"GitHub repository '{repo_path}' not found")

            if response.status_code == 200:
                commits = response.json()
                self._process_github_commits(commits)
                print(f"✅ Fetched {len(commits)} GitHub commits from {repo_path}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to GitHub: {str(e)}")

    def _sync_gitlab_commits(self):
        """Fetch commits from GitLab"""
        repo_path = self.get_repo_path()
        if not repo_path:
            raise IntegrationError("Invalid GitLab repository URL")

        headers = self.get_headers()
        since = datetime.utcnow() - timedelta(days=30)
        project_id = repo_path.replace("/", "%2F")

        try:
            response = requests.get(
                f"https://gitlab.com/api/v4/projects/{project_id}/repository/commits",
                headers=headers,
                params={"since": since.isoformat(), "per_page": 100},
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("GitLab authentication failed. Check your token.")

            if response.status_code == 404:
                raise IntegrationError(f"GitLab repository '{repo_path}' not found")

            if response.status_code == 200:
                commits = response.json()
                self._process_gitlab_commits(commits)
                print(f"✅ Fetched {len(commits)} GitLab commits for project {self.project.id}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to GitLab: {str(e)}")

    def _sync_bitbucket_commits(self):
        """Fetch commits from Bitbucket"""
        repo_path = self.get_repo_path()
        if not repo_path:
            raise IntegrationError("Invalid Bitbucket repository URL")

        headers = self.get_headers()

        try:
            response = requests.get(
                f"https://api.bitbucket.org/2.0/repositories/{repo_path}/commits",
                headers=headers,
                params={"pagelen": 100},
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("Bitbucket authentication failed. Check your token.")

            if response.status_code == 404:
                raise IntegrationError(f"Bitbucket repository '{repo_path}' not found")

            if response.status_code == 200:
                commits = response.json().get("values", [])
                self._process_bitbucket_commits(commits)
                print(f"✅ Fetched {len(commits)} Bitbucket commits for project {self.project.id}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Bitbucket: {str(e)}")

    def _process_github_commits(self, commits: List[Dict]):
        """Process GitHub commits for contribution metrics"""
        for commit in commits:
            try:
                external_id = commit["sha"]
                # Check if contribution already exists
                existing_contribution = self.db.query(Contribution).filter(Contribution.external_id == external_id).first()
                if existing_contribution:
                    continue

                # Get GitHub author ID instead of email
                author_data = commit.get("author")
                github_author_id = str(author_data["id"]) if author_data and "id" in author_data else None

                if github_author_id:
                    user_id = self._get_user_from_external_id("github", github_author_id)
                    if user_id:
                        new_contribution = Contribution(
                            user_id=user_id,
                            project_id=self.project.id,
                            source="github",
                            type="commit",
                            external_id=external_id,
                            message=commit["commit"]["message"],
                            timestamp=commit["commit"]["author"]["date"],
                            url=commit["html_url"]
                        )
                        self.db.add(new_contribution)
                    else:
                        print(f"⚠️  GitHub commit by unmapped user {github_author_id}")
            except Exception as e:
                print(f"⚠️  Error processing GitHub commit: {str(e)}")
                continue
        self.db.commit()

    def _process_gitlab_commits(self, commits: List[Dict]):
        """Process GitLab commits for contribution metrics"""
        for commit in commits:
            try:
                external_id = commit["id"]
                # Check if contribution already exists
                existing_contribution = self.db.query(Contribution).filter(Contribution.external_id == external_id).first()
                if existing_contribution:
                    continue

                # Get GitLab author ID
                gitlab_author_id = str(commit.get("author_id")) if commit.get("author_id") else None

                if gitlab_author_id:
                    user_id = self._get_user_from_external_id("gitlab", gitlab_author_id)
                    if user_id:
                        new_contribution = Contribution(
                            user_id=user_id,
                            project_id=self.project.id,
                            source="gitlab",
                            type="commit",
                            external_id=external_id,
                            message=commit["message"],
                            timestamp=commit["authored_date"],
                            url=commit["web_url"]
                        )
                        self.db.add(new_contribution)
                    else:
                        print(f"⚠️  GitLab commit by unmapped user {gitlab_author_id}")
            except Exception as e:
                print(f"⚠️  Error processing GitLab commit: {str(e)}")
                continue
        self.db.commit()

    def _process_bitbucket_commits(self, commits: List[Dict]):
        """Process Bitbucket commits for contribution metrics"""
        for commit in commits:
            try:
                external_id = commit["hash"]
                # Check if contribution already exists
                existing_contribution = self.db.query(Contribution).filter(Contribution.external_id == external_id).first()
                if existing_contribution:
                    continue

                # Get Bitbucket author UUID
                bitbucket_author_id = commit.get("author", {}).get("uuid")

                if bitbucket_author_id:
                    user_id = self._get_user_from_external_id("bitbucket", bitbucket_author_id)
                    if user_id:
                        new_contribution = Contribution(
                            user_id=user_id,
                            project_id=self.project.id,
                            source="bitbucket",
                            type="commit",
                            external_id=external_id,
                            message=commit["message"],
                            timestamp=commit["date"],
                            url=commit["links"]["html"]["href"]
                        )
                        self.db.add(new_contribution)
                    else:
                        print(f"⚠️  Bitbucket commit by unmapped user {bitbucket_author_id}")
            except Exception as e:
                print(f"⚠️  Error processing Bitbucket commit: {str(e)}")
                continue
        self.db.commit()


# ============================================================================
# COMMUNICATION TOOLS SYNC (Slack, Discord, Teams)
# ============================================================================

class CommunicationSync(BaseIntegrationSync):
    """Sync for Communication Tools (Slack, Discord, Teams)"""

    def is_configured(self) -> bool:
        """Check if any Comm resources are linked"""
        comm_providers = ["slack", "discord", "teams"]
        return any(
            r.connection.provider in comm_providers
            for r in self.project.resources
        )

    def sync_activity(self):
        """Sync communication activity metrics"""
        if not self.is_configured():
            print(f"⚠️  No communication resources linked for project {self.project.id}")
            return

        for resource in self.project.resources:
            try:
                provider = resource.connection.provider
                if provider == "slack":
                    self._sync_slack_activity(resource)
                elif provider == "discord":
                    self._sync_discord_activity(resource)
                elif provider == "teams":
                    self._sync_teams_activity(resource)

            except IntegrationError as e:
                print(f"❌ Comm Integration Error ({provider}): {str(e)}")
                self._store_integration_error(str(e))

            except Exception as e:
                print(f"❌ Unexpected comm error ({provider}): {str(e)}")
                self._store_integration_error(f"Comm sync failed: {str(e)}")

    def _sync_slack_activity(self, resource):
        """Fetch Slack channel activity"""
        channel_id = resource.resource_id
        token = resource.connection.access_token # Slack uses access tokens usually

        if not token:
             # Fallback to API key if stored there
             token = resource.connection.api_key

        if not token:
            raise IntegrationError("Missing Slack credentials")

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(
                "https://slack.com/api/conversations.history",
                headers=headers,
                params={"channel": channel_id, "limit": 100},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if not data.get("ok"):
                    raise IntegrationError(f"Slack API error: {data.get('error')}")

                messages = data.get("messages", [])
                self._process_slack_messages(messages, channel_id)
                print(f"✅ Fetched {len(messages)} Slack messages from {resource.resource_name}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Slack: {str(e)}")

    def _process_slack_messages(self, messages: List[Dict], channel_id: str):
        """Process Slack messages for activity metrics"""
        for message in messages:
            try:
                external_id = message["ts"]
                # Check if activity already exists
                existing_activity = self.db.query(Activity).filter(Activity.external_id == external_id).first()
                if existing_activity:
                    continue

                # Get Slack user ID
                slack_user_id = message.get("user")

                if slack_user_id:
                    user_id = self._get_user_from_external_id("slack", slack_user_id)
                    if user_id:
                        new_activity = Activity(
                            user_id=user_id,
                            project_id=self.project.id,
                            source="slack",
                            type="message",
                            external_id=external_id,
                            content=message["text"],
                            timestamp=datetime.fromtimestamp(float(external_id)),
                            channel=channel_id,
                            url=f"https://slack.com/archives/{channel_id}/p{external_id.replace('.', '')}"
                        )
                        self.db.add(new_activity)
                    else:
                        print(f"⚠️  Slack message by unmapped user {slack_user_id}")
            except Exception as e:
                print(f"⚠️  Error processing Slack message: {str(e)}")
                continue
        self.db.commit()

    def _sync_discord_activity(self):
        """Fetch Discord channel activity"""
        if not self.project.comm_channel_id:
            raise IntegrationError("Discord channel ID is required")

        headers = {"Authorization": f"Bot {self.project.comm_api_key}"}

        try:
            response = requests.get(
                f"https://discord.com/api/v10/channels/{self.project.comm_channel_id}/messages",
                headers=headers,
                params={"limit": 100},
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("Discord authentication failed. Check your bot token.")

            if response.status_code == 404:
                raise IntegrationError(f"Discord channel '{self.project.comm_channel_id}' not found")

            if response.status_code == 200:
                messages = response.json()
                self._process_discord_messages(messages)
                print(f"✅ Fetched {len(messages)} Discord messages for project {self.project.id}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Discord: {str(e)}")

    def _process_discord_messages(self, messages: List[Dict]):
        """Process Discord messages for activity metrics"""
        for message in messages:
            try:
                external_id = message["id"]
                # Check if activity already exists
                existing_activity = self.db.query(Activity).filter(Activity.external_id == external_id).first()
                if existing_activity:
                    continue

                # Get Discord author ID
                discord_author_id = message["author"]["id"]

                if discord_author_id:
                    user_id = self._get_user_from_external_id("discord", discord_author_id)
                    if user_id:
                        new_activity = Activity(
                            user_id=user_id,
                            project_id=self.project.id,
                            source="discord",
                            type="message",
                            external_id=external_id,
                            content=message["content"],
                            timestamp=message["timestamp"],
                            channel=message["channel_id"],
                            url=f"https://discord.com/channels/{self.project.organization_id}/{message['channel_id']}/{external_id}"
                        )
                        self.db.add(new_activity)
                    else:
                        print(f"⚠️  Discord message by unmapped user {discord_author_id}")
            except Exception as e:
                print(f"⚠️  Error processing Discord message: {str(e)}")
                continue
        self.db.commit()

    def _sync_teams_activity(self):
        """Fetch Microsoft Teams activity"""
        # Teams integration typically requires OAuth2 and Microsoft Graph API
        print(f"ℹ️  Teams sync not yet implemented for project {self.project.id}")
        # TODO: Implement Teams sync using Microsoft Graph API


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def sync_project_integrations(project_id: int, db: Session) -> Dict[str, str]:
    """
    Sync all integrations for a specific project
    Returns dict with sync status for each integration
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        return {"error": f"Project {project_id} not found"}

    results = {}

    # Sync PM Tool
    pm_sync = PMToolSync(project, db)
    if pm_sync.is_configured():
        try:
            print(f"🔄 Syncing PM tools for project {project_id}...")
            pm_sync.sync_tasks()
            results["pm_tool"] = "success"
        except Exception as e:
            results["pm_tool"] = f"error: {str(e)}"
    else:
        results["pm_tool"] = "not_configured"

    # Sync Version Control
    vc_sync = VersionControlSync(project, db)
    if vc_sync.is_configured():
        try:
            print(f"🔄 Syncing VC tools for project {project_id}...")
            vc_sync.sync_commits()
            results["version_control"] = "success"
        except Exception as e:
            results["version_control"] = f"error: {str(e)}"
    else:
        results["version_control"] = "not_configured"

    # Sync Communication
    comm_sync = CommunicationSync(project, db)
    if comm_sync.is_configured():
        try:
            print(f"🔄 Syncing comm tool ({project.comm_tool}) for project {project_id}...")
            comm_sync.sync_activity()
            results["communication"] = "success"
        except Exception as e:
            results["communication"] = f"error: {str(e)}"
    else:
        results["communication"] = "not_configured"

    return results
