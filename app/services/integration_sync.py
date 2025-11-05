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


# ============================================================================
# PROJECT MANAGEMENT TOOLS SYNC (Jira, Linear, ClickUp)
# ============================================================================

class PMToolSync(BaseIntegrationSync):
    """Sync for Project Management Tools (Jira, Linear, ClickUp)"""

    def is_configured(self) -> bool:
        """Check if PM tool is configured"""
        configured = bool(
            self.project.pm_tool and
            self.project.pm_integration_method and
            (self.project.pm_api_key or self.project.pm_access_token)
        )

        # For Jira, also need workspace URL
        if self.project.pm_tool == "jira":
            configured = configured and bool(self.project.pm_workspace_url)

        return configured

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
        """Sync tasks from PM tool to database"""
        if not self.is_configured():
            print(f"⚠️  PM tool not fully configured for project {self.project.id}")
            return

        try:
            if self.project.pm_tool == "jira":
                self._sync_jira_issues()
            elif self.project.pm_tool == "linear":
                self._sync_linear_issues()
            elif self.project.pm_tool == "clickup":
                self._sync_clickup_tasks()

        except IntegrationError as e:
            print(f"❌ Integration Error: {str(e)}")
            self._store_integration_error(str(e))

        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            self._store_integration_error(f"Sync failed: {str(e)}")

    def _sync_jira_issues(self):
        """Fetch and sync Jira issues"""
        if not self.project.pm_project_id:
            raise IntegrationError("Jira project key is required (e.g., 'TEAM', 'PROD')")

        api_url = self.get_api_url()
        headers = self.get_headers()
        workspace = self.get_jira_workspace_url()

        try:
            response = requests.get(
                f"{api_url}/search",
                headers=headers,
                params={
                    "jql": f"project={self.project.pm_project_id}",
                    "maxResults": 100,
                    "fields": "summary,description,status,assignee,duedate"
                },
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("Jira authentication failed. Check your API key/token.")

            if response.status_code == 400:
                error_msg = response.json().get("errorMessages", ["Unknown error"])[0]
                raise IntegrationError(f"Jira request error: {error_msg}")

            if response.status_code == 404:
                raise IntegrationError(
                    f"Jira project '{self.project.pm_project_id}' not found on '{workspace}'"
                )

            if response.status_code != 200:
                raise IntegrationError(f"Jira API error: {response.status_code}")

            issues = response.json().get("issues", [])
            self._save_tasks_to_db(issues, "jira", workspace)
            print(f"✅ Synced {len(issues)} Jira issues for project {self.project.id}")

        except requests.exceptions.Timeout:
            raise IntegrationError("Jira API request timed out")

        except requests.exceptions.ConnectionError:
            raise IntegrationError(f"Cannot connect to Jira workspace '{workspace}'")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Jira: {str(e)}")

    def _sync_linear_issues(self):
        """Fetch and sync Linear issues"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        if not self.project.pm_project_id:
            raise IntegrationError("Linear project ID is required")

        query = """
        query($projectId: String!) {
            issues(filter: {project: {id: {eq: $projectId}}}) {
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
                    "variables": {"projectId": self.project.pm_project_id}
                },
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("Linear authentication failed. Check your API key.")

            if response.status_code == 200:
                data = response.json()
                if "errors" in data:
                    raise IntegrationError(f"Linear API error: {data['errors'][0]['message']}")

                issues = data.get("data", {}).get("issues", {}).get("nodes", [])
                self._save_tasks_to_db(issues, "linear")
                print(f"✅ Synced {len(issues)} Linear issues for project {self.project.id}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Linear: {str(e)}")

    def _sync_clickup_tasks(self):
        """Fetch and sync ClickUp tasks"""
        api_url = self.get_api_url()
        headers = self.get_headers()

        try:
            response = requests.get(api_url, headers=headers, timeout=30)

            if response.status_code == 401:
                raise IntegrationError("ClickUp authentication failed. Check your API key.")

            if response.status_code == 404:
                raise IntegrationError(f"ClickUp list '{self.project.pm_project_id}' not found")

            if response.status_code == 200:
                tasks = response.json().get("tasks", [])
                self._save_tasks_to_db(tasks, "clickup")
                print(f"✅ Synced {len(tasks)} ClickUp tasks for project {self.project.id}")

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
                    assignee_email = ext_task["fields"].get("assignee", {}).get("emailAddress")
                    due_date = ext_task["fields"].get("duedate")
                    url = f"https://{workspace}/browse/{ext_task['key']}"

                elif source == "linear":
                    task_id = ext_task["id"]
                    title = ext_task["title"]
                    description = ext_task.get("description")
                    status_name = ext_task["state"]["name"]
                    assignee_email = ext_task.get("assignee", {}).get("email")
                    due_date = ext_task.get("dueDate")
                    url = ext_task["url"]

                elif source == "clickup":
                    task_id = ext_task["id"]
                    title = ext_task["name"]
                    description = ext_task.get("description")
                    status_name = ext_task["status"]["status"]
                    assignees = ext_task.get("assignees", [])
                    assignee_email = assignees[0].get("email") if assignees else None
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

                # Map assignee to local user
                if assignee_email:
                    user = self.db.query(User).filter(User.email == assignee_email).first()
                    if user:
                        task.owner_id = user.id

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
        """Check if VC is configured"""
        return bool(
            self.project.vc_tool and
            self.project.vc_repository_url and
            (self.project.vc_api_key or self.project.vc_access_token)
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
        """Sync recent commits to track contribution metrics"""
        if not self.is_configured():
            print(f"⚠️  VC not configured for project {self.project.id}")
            return

        try:
            if self.project.vc_tool == "github":
                self._sync_github_commits()
            elif self.project.vc_tool == "gitlab":
                self._sync_gitlab_commits()
            elif self.project.vc_tool == "bitbucket":
                self._sync_bitbucket_commits()

        except IntegrationError as e:
            print(f"❌ VC Integration Error: {str(e)}")
            self._store_integration_error(str(e))

        except Exception as e:
            print(f"❌ Unexpected VC error: {str(e)}")
            self._store_integration_error(f"VC sync failed: {str(e)}")

    def _sync_github_commits(self):
        """Fetch commits from GitHub"""
        repo_path = self.get_repo_path()
        if not repo_path:
            raise IntegrationError("Invalid GitHub repository URL")

        headers = self.get_headers()
        since = datetime.utcnow() - timedelta(days=30)

        try:
            response = requests.get(
                f"https://api.github.com/repos/{repo_path}/commits",
                headers=headers,
                params={"since": since.isoformat(), "per_page": 100},
                timeout=30
            )

            if response.status_code == 401:
                raise IntegrationError("GitHub authentication failed. Check your token.")

            if response.status_code == 404:
                raise IntegrationError(f"GitHub repository '{repo_path}' not found")

            if response.status_code == 200:
                commits = response.json()
                self._process_github_commits(commits)
                print(f"✅ Fetched {len(commits)} GitHub commits for project {self.project.id}")

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
            author_email = commit["commit"]["author"].get("email")
            if author_email:
                user = self.db.query(User).filter(User.email == author_email).first()
                if user:
                    # TODO: Update user's contribution metrics in dashboard
                    pass

    def _process_gitlab_commits(self, commits: List[Dict]):
        """Process GitLab commits for contribution metrics"""
        for commit in commits:
            author_email = commit.get("author_email")
            if author_email:
                user = self.db.query(User).filter(User.email == author_email).first()
                if user:
                    # TODO: Update user's contribution metrics
                    pass

    def _process_bitbucket_commits(self, commits: List[Dict]):
        """Process Bitbucket commits for contribution metrics"""
        for commit in commits:
            author_email = commit["author"]["user"].get("email")
            if author_email:
                user = self.db.query(User).filter(User.email == author_email).first()
                if user:
                    # TODO: Update user's contribution metrics
                    pass


# ============================================================================
# COMMUNICATION TOOLS SYNC (Slack, Discord, Teams)
# ============================================================================

class CommunicationSync(BaseIntegrationSync):
    """Sync for Communication Tools (Slack, Discord, Teams)"""

    def is_configured(self) -> bool:
        """Check if comm tool is configured"""
        return bool(
            self.project.comm_tool and
            self.project.comm_integration_method and
            (self.project.comm_webhook_url or self.project.comm_api_key)
        )

    def sync_activity(self):
        """Sync communication activity metrics"""
        if not self.is_configured():
            print(f"⚠️  Communication tool not configured for project {self.project.id}")
            return

        try:
            if self.project.comm_integration_method == IntegrationMethod.WEBHOOK:
                print(f"ℹ️  Webhook configured for {self.project.comm_tool}")
                # Webhooks are passive - they listen for events
                return

            if self.project.comm_integration_method == IntegrationMethod.API_KEY:
                if self.project.comm_tool == "slack":
                    self._sync_slack_activity()
                elif self.project.comm_tool == "discord":
                    self._sync_discord_activity()
                elif self.project.comm_tool == "teams":
                    self._sync_teams_activity()

        except IntegrationError as e:
            print(f"❌ Comm Integration Error: {str(e)}")
            self._store_integration_error(str(e))

        except Exception as e:
            print(f"❌ Unexpected comm error: {str(e)}")
            self._store_integration_error(f"Comm sync failed: {str(e)}")

    def _sync_slack_activity(self):
        """Fetch Slack channel activity"""
        if not self.project.comm_channel_id:
            raise IntegrationError("Slack channel ID is required")

        headers = {"Authorization": f"Bearer {self.project.comm_api_key}"}

        try:
            response = requests.get(
                "https://slack.com/api/conversations.history",
                headers=headers,
                params={"channel": self.project.comm_channel_id, "limit": 100},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if not data.get("ok"):
                    raise IntegrationError(f"Slack API error: {data.get('error')}")

                messages = data.get("messages", [])
                print(f"✅ Fetched {len(messages)} Slack messages for project {self.project.id}")
                # TODO: Process messages for team activity metrics

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Slack: {str(e)}")

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
                print(f"✅ Fetched {len(messages)} Discord messages for project {self.project.id}")

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Discord: {str(e)}")

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
            print(f"🔄 Syncing PM tool ({project.pm_tool}) for project {project_id}...")
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
            print(f"🔄 Syncing VC ({project.vc_tool}) for project {project_id}...")
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
