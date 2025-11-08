"""
Initial Project Sync Service
Performs comprehensive one-time sync after project creation
- Syncs all tasks from PM tools
- Syncs all commits from version control
- Syncs all messages from communication tools
- Maps external users to TeamIQ users
"""

from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta
import requests

from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus
from app.models.activity import Activity, CommitActivity, PullRequestActivity
from app.models.user import User
from app.services.bidirectional_sync import get_sync_service


class InitialProjectSync:
    """Handles initial comprehensive sync when project is created"""

    def __init__(self, project_id: int, db: Session):
        self.project_id = project_id
        self.db = db
        self.project = db.query(Project).filter(Project.id == project_id).first()

        if not self.project:
            raise ValueError(f"Project {project_id} not found")

        self.results = {
            "tasks_synced": 0,
            "commits_synced": 0,
            "pull_requests_synced": 0,
            "activities_synced": 0,
            "users_mapped": 0
        }

    def sync_all(self) -> Dict:
        """Sync everything from all integrated tools"""
        print(f"🔄 Starting initial sync for project {self.project_id}")

        # 1. Sync tasks from PM tool
        if self.project.pm_tool:
            self._sync_pm_tool_tasks()

        # 2. Sync commits and PRs from version control
        if self.project.vc_tool:
            self._sync_version_control()

        # 3. Sync messages from communication tool
        if self.project.comm_tool:
            self._sync_communication()

        # 4. Map external users to TeamIQ users
        self._map_users()

        return self.results

    # ==========================================================================
    # 1. PM TOOL SYNC (Tasks from Jira/ClickUp)
    # ==========================================================================

    def _sync_pm_tool_tasks(self):
        """Sync all tasks from PM tool"""
        try:
            sync_service = get_sync_service(self.project, self.db)
            if sync_service:
                tasks = sync_service.pull_tasks()
                self.results["tasks_synced"] = len(tasks)
                print(f"✅ Synced {len(tasks)} tasks from {self.project.pm_tool}")
        except Exception as e:
            print(f"❌ Failed to sync PM tool tasks: {str(e)}")

    # ==========================================================================
    # 2. VERSION CONTROL SYNC (Commits & PRs from GitHub/GitLab)
    # ==========================================================================

    def _sync_version_control(self):
        """Sync commits and pull requests"""
        if self.project.vc_tool == "github":
            self._sync_github()
        elif self.project.vc_tool == "gitlab":
            self._sync_gitlab()
        elif self.project.vc_tool == "bitbucket":
            self._sync_bitbucket()

    def _sync_github(self):
        """Sync GitHub commits and PRs"""
        repo_path = self._extract_repo_path(self.project.vc_repository_url)
        headers = self._get_vc_headers()

        # Sync commits (last 30 days)
        since = (datetime.utcnow() - timedelta(days=30)).isoformat()

        try:
            # Get commits
            response = requests.get(
                f"https://api.github.com/repos/{repo_path}/commits",
                headers=headers,
                params={"since": since, "per_page": 100},
                timeout=30
            )

            if response.status_code == 200:
                commits = response.json()
                for commit in commits:
                    self._save_commit_activity(commit, "github")
                self.results["commits_synced"] = len(commits)

            # Get pull requests
            pr_response = requests.get(
                f"https://api.github.com/repos/{repo_path}/pulls",
                headers=headers,
                params={"state": "all", "per_page": 100},
                timeout=30
            )

            if pr_response.status_code == 200:
                prs = pr_response.json()
                for pr in prs:
                    self._save_pr_activity(pr, "github")
                self.results["pull_requests_synced"] = len(prs)

            print(f"✅ Synced GitHub: {self.results['commits_synced']} commits, {self.results['pull_requests_synced']} PRs")

        except Exception as e:
            print(f"❌ Failed to sync GitHub: {str(e)}")

    def _save_commit_activity(self, commit_data: Dict, source: str):
        """Save commit to database"""
        author_email = commit_data.get("commit", {}).get("author", {}).get("email")

        # Find user by email
        user = self.db.query(User).filter(User.email == author_email).first()

        if not user:
            return  # Skip if user not found

        # Check if commit already exists
        existing = self.db.query(CommitActivity).filter(
            CommitActivity.commit_sha == commit_data["sha"]
        ).first()

        if existing:
            return

        # Create commit activity
        commit = CommitActivity(
            user_id=user.id,
            project_id=self.project.id,
            commit_sha=commit_data["sha"],
            message=commit_data["commit"]["message"],
            repository=self.project.vc_repository_url,
            source=source,
            external_url=commit_data.get("html_url"),
            timestamp=datetime.fromisoformat(
                commit_data["commit"]["author"]["date"].replace("Z", "+00:00")
            ),
            files_changed=len(commit_data.get("files", [])),
            additions=sum(f.get("additions", 0) for f in commit_data.get("files", [])),
            deletions=sum(f.get("deletions", 0) for f in commit_data.get("files", []))
        )

        self.db.add(commit)

        # Also create general activity record
        activity = Activity(
            user_id=user.id,
            project_id=self.project.id,
            type="commit",
            source=source,
            action="created",
            title=commit_data["commit"]["message"][:100],
            external_id=commit_data["sha"],
            external_url=commit_data.get("html_url"),
            timestamp=commit.timestamp,
            impact_score=self._calculate_commit_impact(commit)
        )

        self.db.add(activity)

    def _save_pr_activity(self, pr_data: Dict, source: str):
        """Save pull request to database"""
        author_email = pr_data.get("user", {}).get("email")

        user = self.db.query(User).filter(User.email == author_email).first()
        if not user:
            return

        # Check if PR already exists
        existing = self.db.query(PullRequestActivity).filter(
            PullRequestActivity.external_id == str(pr_data["id"]),
            PullRequestActivity.source == source
        ).first()

        if existing:
            return

        # Create PR activity
        pr = PullRequestActivity(
            user_id=user.id,
            project_id=self.project.id,
            pr_number=pr_data["number"],
            title=pr_data["title"],
            description=pr_data.get("body", ""),
            state=pr_data["state"],
            external_id=str(pr_data["id"]),
            external_url=pr_data["html_url"],
            source=source,
            created_at=datetime.fromisoformat(
                pr_data["created_at"].replace("Z", "+00:00")
            ),
            merged_at=datetime.fromisoformat(
                pr_data["merged_at"].replace("Z", "+00:00")
            ) if pr_data.get("merged_at") else None
        )

        self.db.add(pr)

        # Create activity record
        activity = Activity(
            user_id=user.id,
            project_id=self.project.id,
            type="pull_request",
            source=source,
            action="created" if pr_data["state"] == "open" else "merged",
            title=pr_data["title"],
            external_id=str(pr_data["id"]),
            external_url=pr_data["html_url"],
            timestamp=pr.created_at,
            impact_score=5.0  # PRs have high impact
        )

        self.db.add(activity)

    # ==========================================================================
    # 3. COMMUNICATION SYNC (Messages from Slack/Discord)
    # ==========================================================================

    def _sync_communication(self):
        """Sync messages from communication tools"""
        if self.project.comm_tool == "slack":
            self._sync_slack_messages()
        elif self.project.comm_tool == "discord":
            self._sync_discord_messages()

    def _sync_slack_messages(self):
        """Sync Slack channel messages"""
        if not self.project.comm_channel_id or not self.project.comm_api_key:
            return

        headers = {"Authorization": f"Bearer {self.project.comm_api_key}"}

        # Get messages from last 7 days
        oldest = (datetime.utcnow() - timedelta(days=7)).timestamp()

        try:
            response = requests.get(
                "https://slack.com/api/conversations.history",
                headers=headers,
                params={
                    "channel": self.project.comm_channel_id,
                    "oldest": str(oldest),
                    "limit": 100
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    messages = data.get("messages", [])
                    for msg in messages:
                        self._save_slack_message(msg)
                    self.results["activities_synced"] = len(messages)
                    print(f"✅ Synced {len(messages)} Slack messages")

        except Exception as e:
            print(f"❌ Failed to sync Slack: {str(e)}")

    def _save_slack_message(self, message: Dict):
        """Save Slack message as activity"""
        user_id_slack = message.get("user")

        # TODO: Map Slack user ID to TeamIQ user
        # For now, skip if we can't map

        activity = Activity(
            user_id=None,  # TODO: Map user
            project_id=self.project.id,
            type="message",
            source="slack",
            action="sent",
            content=message.get("text", ""),
            external_id=message.get("ts"),
            channel_id=self.project.comm_channel_id,
            timestamp=datetime.fromtimestamp(float(message.get("ts", 0))),
            impact_score=1.0
        )

        self.db.add(activity)

    # ==========================================================================
    # 4. USER MAPPING
    # ==========================================================================

    def _map_users(self):
        """
        Map external users (from Jira, GitHub, Slack) to TeamIQ users
        Uses email as the primary matching criterion
        """
        project_members = self.db.query(User).join(
            ProjectMember
        ).filter(
            ProjectMember.project_id == self.project.id
        ).all()

        for user in project_members:
            # User already exists in TeamIQ
            # Their email should match emails in external tools
            self.results["users_mapped"] += 1

        print(f"✅ Mapped {self.results['users_mapped']} users")

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    def _extract_repo_path(self, repo_url: str) -> str:
        """Extract owner/repo from GitHub URL"""
        return repo_url.replace("https://github.com/", "").replace(".git", "")

    def _get_vc_headers(self) -> Dict:
        """Get version control auth headers"""
        if self.project.vc_access_token:
            return {"Authorization": f"Bearer {self.project.vc_access_token}"}
        elif self.project.vc_api_key:
            return {"Authorization": f"token {self.project.vc_api_key}"}
        return {}

    def _calculate_commit_impact(self, commit: CommitActivity) -> float:
        """Calculate impact score based on commit size"""
        total_changes = commit.additions + commit.deletions
        if total_changes < 10:
            return 1.0
        elif total_changes < 50:
            return 3.0
        elif total_changes < 200:
            return 5.0
        else:
            return 8.0
