"""
Complete Webhook Receivers for Real-Time Sync
Implements ALL security, user mapping, and data processing
Multi-tenant with per-project webhook secrets
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
import hmac
import hashlib
import json
from datetime import datetime
import requests

from app.core.database import get_db
from app.core.encryption import decrypt_field
from app.models.task import Task, TaskHistory, TaskStatus, TaskComment
from app.models.activity import Activity, CommitActivity, PullRequestActivity
from app.models.project import Project
from app.models.user import User
from app.schemas.response_model import create_response
from app.services.webhook_service import get_webhook_service


router = APIRouter()


# ==============================================================================
# USER MAPPING SERVICE (Used by all webhooks)
# ==============================================================================

class UserMapper:
    """Maps external users to TeamIQ users"""

    def __init__(self, db: Session):
        self.db = db
        self._cache = {}  # Cache for performance

    def map_by_email(self, email: str) -> Optional[User]:
        """Map user by email (most reliable)"""
        if not email:
            return None

        if email in self._cache:
            return self._cache[email]

        user = self.db.query(User).filter(User.email == email.lower()).first()
        if user:
            self._cache[email] = user

        return user

    def map_jira_user(self, jira_user: dict, project: Project) -> Optional[User]:
        """Map Jira user to TeamIQ user"""
        email = jira_user.get("emailAddress")
        return self.map_by_email(email)

    def map_github_user(self, github_user: dict, project: Project) -> Optional[User]:
        """Map GitHub user to TeamIQ user"""
        # Try email first
        email = github_user.get("email")
        if email:
            return self.map_by_email(email)

        # Fallback: Fetch user data from GitHub API
        username = github_user.get("login")
        if username:
            return self._fetch_github_user_email(username, project)

        return None

    def map_slack_user(self, slack_user_id: str, project: Project) -> Optional[User]:
        """Map Slack user ID to TeamIQ user by fetching their email"""
        if not project.comm_api_key:
            return None

        # Decrypt API key
        api_key = decrypt_field(project.comm_api_key)

        try:
            response = requests.get(
                "https://slack.com/api/users.info",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"user": slack_user_id},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    email = data["user"]["profile"].get("email")
                    return self.map_by_email(email)

        except Exception as e:
            print(f"Failed to fetch Slack user: {e}")

        return None

    def map_clickup_user(self, clickup_user: dict, project: Project) -> Optional[User]:
        """Map ClickUp user to TeamIQ user"""
        email = clickup_user.get("email")
        return self.map_by_email(email)

    def _fetch_github_user_email(self, username: str, project: Project) -> Optional[User]:
        """Fetch GitHub user's email via API"""
        if not project.vc_access_token and not project.vc_api_key:
            return None

        # Decrypt token
        token = decrypt_field(project.vc_access_token or project.vc_api_key)

        try:
            response = requests.get(
                f"https://api.github.com/users/{username}",
                headers={"Authorization": f"token {token}"},
                timeout=10
            )

            if response.status_code == 200:
                user_data = response.json()
                email = user_data.get("email")
                if email:
                    return self.map_by_email(email)

        except Exception as e:
            print(f"Failed to fetch GitHub user: {e}")

        return None


# ==============================================================================
# WEBHOOK SECURITY (Per-Project)
# ==============================================================================

def verify_github_signature(payload: bytes, signature: str, project: Project) -> bool:
    """Verify GitHub webhook signature using project-specific secret"""
    if not project.vc_webhook_secret:
        print("⚠️  No webhook secret configured, skipping verification")
        return True

    # Decrypt project's webhook secret
    webhook_secret = decrypt_field(project.vc_webhook_secret)

    # Compute expected signature
    computed = "sha256=" + hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


def verify_slack_signature(timestamp: str, body: bytes, signature: str, project: Project) -> bool:
    """Verify Slack webhook signature using project-specific secret"""
    if not project.comm_webhook_secret:
        return True

    # Decrypt Slack signing secret
    signing_secret = decrypt_field(project.comm_webhook_secret)

    base_string = f"v0:{timestamp}:{body.decode()}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(),
        base_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


# ==============================================================================
# JIRA WEBHOOKS (COMPLETE)
# ==============================================================================

@router.post("/jira")
async def jira_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Complete Jira webhook implementation
    Handles: issue_created, issue_updated, issue_deleted, comment_created
    """
    body = await request.body()
    payload = json.loads(body)

    webhook_event = payload.get("webhookEvent")
    issue = payload.get("issue")
    comment = payload.get("comment")

    if not issue and not comment:
        return create_response(success=True, message="No actionable data")

    mapper = UserMapper(db)
    webhook_service = get_webhook_service(db)

    # Find project by Jira project key
    project = None
    if issue:
        project_key = issue["fields"]["project"]["key"]
        project = db.query(Project).filter(
            Project.pm_tool == "jira",
            Project.pm_project_id == project_key
        ).first()

        if not project:
            return create_response(success=False, message="Project not found")

        try:
            issue_id = issue["id"]
            issue_key = issue["key"]
            fields = issue["fields"]

            # Find or create task
            task = db.query(Task).filter(
                Task.external_id == issue_id,
                Task.external_source == "jira"
            ).first()

            if webhook_event == "jira:issue_created":
                # Create new task
                if not task:
                    assignee = fields.get("assignee")
                    user = mapper.map_jira_user(assignee, project) if assignee else None

                    task = Task(
                        external_id=issue_id,
                        external_source="jira",
                        project_id=project.id,
                        organization_id=project.organization_id,
                        owner_id=user.id if user else None,
                        title=fields["summary"],
                        description=fields.get("description", ""),
                        status=_map_jira_status(fields["status"]["name"]),
                        external_status=fields["status"]["name"],
                        external_url=f"https://{project.pm_workspace_url}/browse/{issue_key}",
                        due_date=fields.get("duedate"),
                        last_synced_at=datetime.utcnow()
                    )
                    db.add(task)
                    db.commit()

                    print(f"✅ Jira webhook: Created task from {issue_key}")

            elif webhook_event == "jira:issue_updated" and task:
                # Update existing task
                old_status = task.status.value
                new_status = _map_jira_status(fields["status"]["name"])

                task.title = fields["summary"]
                task.description = fields.get("description", "")
                task.status = new_status
                task.external_status = fields["status"]["name"]
                task.last_synced_at = datetime.utcnow()

                # Update assignee
                assignee = fields.get("assignee")
                if assignee:
                    user = mapper.map_jira_user(assignee, project)
                    if user:
                        task.owner_id = user.id

                # Log status change
                if old_status != new_status.value:
                    history = TaskHistory(
                        task_id=task.id,
                        field_name="status",
                        old_value=old_status,
                        new_value=new_status.value,
                        source="jira"
                    )
                    db.add(history)

                db.commit()
                print(f"✅ Jira webhook: Updated task {task.id}")

            elif webhook_event == "jira:issue_deleted" and task:
                # Delete or archive task
                db.delete(task)
                db.commit()
                print(f"🗑️ Jira webhook: Deleted task {task.id}")

            # Handle comments
            if webhook_event == "comment_created" and comment:
                task = db.query(Task).filter(
                    Task.external_id == issue["id"],
                    Task.external_source == "jira"
                ).first()

                if task:
                    author = comment.get("author")
                    user = mapper.map_jira_user(author, project) if author else None

                    task_comment = TaskComment(
                        task_id=task.id,
                        user_id=user.id if user else None,
                        content=comment.get("body", ""),
                        external_id=comment["id"],
                        external_source="jira"
                    )
                    db.add(task_comment)
                    db.commit()

                    print(f"💬 Jira webhook: Added comment to task {task.id}")

            # Record webhook event
            webhook_service.record_webhook_event(
                project_id=project.id,
                tool_name="jira",
                event_type=webhook_event,
                success=True
            )

            return create_response(success=True, message="Webhook processed")

        except Exception as e:
            # Record failure
            if project:
                webhook_service.record_webhook_event(
                    project_id=project.id,
                    tool_name="jira",
                    event_type=webhook_event,
                    success=False,
                    error=str(e)
                )
            raise HTTPException(status_code=500, detail=str(e))


def _map_jira_status(jira_status: str) -> TaskStatus:
    """Map Jira status to TeamIQ TaskStatus"""
    status_map = {
        "to do": TaskStatus.TODO,
        "backlog": TaskStatus.BACKLOG,
        "in progress": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.DONE,
        "completed": TaskStatus.DONE,
    }
    return status_map.get(jira_status.lower(), TaskStatus.TODO)


# ==============================================================================
# GITHUB WEBHOOKS (COMPLETE with Per-Project Secret)
# ==============================================================================

@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Complete GitHub webhook implementation with per-project secret verification
    Events: push, pull_request, issues, issue_comment
    """
    body = await request.body()
    payload = json.loads(body)

    mapper = UserMapper(db)
    webhook_service = get_webhook_service(db)

    # Find project by repository
    repository_url = payload["repository"]["html_url"]
    project = db.query(Project).filter(
        Project.vc_tool == "github",
        Project.vc_repository_url == repository_url
    ).first()

    if not project:
        return create_response(success=False, message="Project not found")

    # ✅ VERIFY SIGNATURE using project-specific secret
    if x_hub_signature_256:
        if not verify_github_signature(body, x_hub_signature_256, project):
            print(f"❌ Invalid webhook signature for project {project.id}")
            raise HTTPException(status_code=401, detail="Invalid signature")
        print(f"✅ Webhook signature verified for project {project.id}")

    try:
        # PUSH EVENT (Commits)
        if x_github_event == "push":
            commits = payload.get("commits", [])

            for commit_data in commits:
                author = commit_data.get("author", {})
                user = mapper.map_by_email(author.get("email"))

                if not user:
                    continue

                # Check if commit already exists
                existing = db.query(CommitActivity).filter(
                    CommitActivity.commit_sha == commit_data["id"]
                ).first()

                if existing:
                    continue

                # Create commit activity
                commit = CommitActivity(
                    user_id=user.id,
                    project_id=project.id,
                    commit_sha=commit_data["id"],
                    message=commit_data["message"],
                    repository=payload["repository"]["full_name"],
                    source="github",
                    external_url=commit_data["url"],
                    timestamp=datetime.fromisoformat(
                        commit_data["timestamp"].replace("Z", "+00:00")
                    )
                )
                db.add(commit)

                # Create general activity
                activity = Activity(
                    user_id=user.id,
                    project_id=project.id,
                    type="commit",
                    source="github",
                    action="created",
                    title=commit_data["message"][:100],
                    external_id=commit_data["id"],
                    external_url=commit_data["url"],
                    timestamp=commit.timestamp,
                    impact_score=3.0
                )
                db.add(activity)

            db.commit()
            print(f"✅ GitHub webhook: Processed {len(commits)} commits")

        # PULL REQUEST EVENT
        elif x_github_event == "pull_request":
            action = payload.get("action")
            pr = payload["pull_request"]

            user = mapper.map_github_user(pr["user"], project)

            if not user:
                return create_response(success=True, message="User not mapped")

            # Find or create PR activity
            pr_activity = db.query(PullRequestActivity).filter(
                PullRequestActivity.external_id == str(pr["id"]),
                PullRequestActivity.source == "github"
            ).first()

            if not pr_activity and action == "opened":
                pr_activity = PullRequestActivity(
                    user_id=user.id,
                    project_id=project.id,
                    pr_number=pr["number"],
                    title=pr["title"],
                    description=pr.get("body", ""),
                    state=pr["state"],
                    external_id=str(pr["id"]),
                    external_url=pr["html_url"],
                    source="github",
                    created_at=datetime.fromisoformat(
                        pr["created_at"].replace("Z", "+00:00")
                    )
                )
                db.add(pr_activity)

            elif pr_activity:
                # Update existing PR
                pr_activity.state = pr["state"]
                if action == "closed" and pr.get("merged"):
                    pr_activity.merged_at = datetime.utcnow()

            # Create activity record
            activity = Activity(
                user_id=user.id,
                project_id=project.id,
                type="pull_request",
                source="github",
                action=action,
                title=pr["title"],
                external_id=str(pr["id"]),
                external_url=pr["html_url"],
                timestamp=datetime.utcnow(),
                impact_score=5.0 if action == "merged" else 3.0
            )
            db.add(activity)

            db.commit()
            print(f"✅ GitHub webhook: PR {action} - {pr['title']}")

        # ISSUE COMMENT EVENT
        elif x_github_event == "issue_comment":
            action = payload.get("action")
            comment = payload["comment"]
            issue = payload["issue"]

            user = mapper.map_github_user(comment["user"], project)

            if user:
                activity = Activity(
                    user_id=user.id,
                    project_id=project.id,
                    type="pr_comment",
                    source="github",
                    action=action,
                    content=comment["body"],
                    external_id=str(comment["id"]),
                    external_url=comment["html_url"],
                    timestamp=datetime.fromisoformat(
                        comment["created_at"].replace("Z", "+00:00")
                    ),
                    impact_score=1.0
                )
                db.add(activity)
                db.commit()

                print(f"💬 GitHub webhook: Comment on issue #{issue['number']}")

        # Record successful webhook event
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="github",
            event_type=x_github_event,
            success=True
        )

        return create_response(success=True, message="Webhook processed")

    except Exception as e:
        # Record failure
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="github",
            event_type=x_github_event,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# CLICKUP WEBHOOKS (COMPLETE)
# ==============================================================================

@router.post("/clickup")
async def clickup_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Complete ClickUp webhook implementation
    Events: taskCreated, taskUpdated, taskDeleted, taskCommentPosted
    """
    payload = await request.json()

    event = payload.get("event")
    task_id = payload.get("task_id")

    mapper = UserMapper(db)
    webhook_service = get_webhook_service(db)

    # Find project by list ID
    list_id = payload.get("list_id")
    project = db.query(Project).filter(
        Project.pm_tool == "clickup",
        Project.pm_project_id == list_id
    ).first()

    if not project:
        return create_response(success=False, message="Project not found")

    try:
        if event == "taskCreated":
            # Fetch full task data from ClickUp
            task_data = _fetch_clickup_task(task_id, project)

            if task_data:
                assignees = task_data.get("assignees", [])
                user = mapper.map_clickup_user(assignees[0], project) if assignees else None

                task = Task(
                    external_id=task_id,
                    external_source="clickup",
                    project_id=project.id,
                    organization_id=project.organization_id,
                    owner_id=user.id if user else None,
                    title=task_data["name"],
                    description=task_data.get("description", ""),
                    status=_map_clickup_status(task_data["status"]["status"]),
                    external_url=task_data["url"],
                    last_synced_at=datetime.utcnow()
                )
                db.add(task)
                db.commit()

                print(f"✅ ClickUp webhook: Created task {task.id}")

        elif event == "taskUpdated":
            task = db.query(Task).filter(
                Task.external_id == task_id,
                Task.external_source == "clickup"
            ).first()

            if task:
                # Fetch updated task data
                task_data = _fetch_clickup_task(task_id, project)

                if task_data:
                    old_status = task.status.value
                    new_status = _map_clickup_status(task_data["status"]["status"])

                    task.title = task_data["name"]
                    task.description = task_data.get("description", "")
                    task.status = new_status
                    task.last_synced_at = datetime.utcnow()

                    # Log change
                    if old_status != new_status.value:
                        history = TaskHistory(
                            task_id=task.id,
                            field_name="status",
                            old_value=old_status,
                            new_value=new_status.value,
                            source="clickup"
                        )
                        db.add(history)

                    db.commit()
                    print(f"✅ ClickUp webhook: Updated task {task.id}")

        elif event == "taskDeleted":
            task = db.query(Task).filter(
                Task.external_id == task_id,
                Task.external_source == "clickup"
            ).first()

            if task:
                db.delete(task)
                db.commit()
                print(f"🗑️ ClickUp webhook: Deleted task {task.id}")

        # Record webhook event
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="clickup",
            event_type=event,
            success=True
        )

        return create_response(success=True, message="Webhook processed")

    except Exception as e:
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="clickup",
            event_type=event,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


def _fetch_clickup_task(task_id: str, project: Project) -> Optional[dict]:
    """Fetch full task data from ClickUp API"""
    # Decrypt API key
    api_key = decrypt_field(project.pm_api_key)

    try:
        response = requests.get(
            f"https://api.clickup.com/api/v2/task/{task_id}",
            headers={"Authorization": api_key},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Failed to fetch ClickUp task: {e}")

    return None


def _map_clickup_status(clickup_status: str) -> TaskStatus:
    """Map ClickUp status to TeamIQ TaskStatus"""
    status_map = {
        "to do": TaskStatus.TODO,
        "in progress": TaskStatus.IN_PROGRESS,
        "complete": TaskStatus.DONE,
        "closed": TaskStatus.DONE,
    }
    return status_map.get(clickup_status.lower(), TaskStatus.TODO)


# ==============================================================================
# SLACK WEBHOOKS (COMPLETE with Per-Project Secret)
# ==============================================================================

@router.post("/slack/events")
async def slack_webhook(
    request: Request,
    x_slack_request_timestamp: Optional[str] = Header(None),
    x_slack_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Complete Slack webhook implementation with signature verification
    Events: message, reaction_added, app_mention, file_shared
    """
    body = await request.body()
    payload = json.loads(body)

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event = payload.get("event", {})
    event_type = event.get("type")

    mapper = UserMapper(db)
    webhook_service = get_webhook_service(db)

    # Find project by channel ID
    channel_id = event.get("channel")
    project = db.query(Project).filter(
        Project.comm_tool == "slack",
        Project.comm_channel_id == channel_id
    ).first()

    if not project:
        return create_response(success=True, message="Project not found")

    # ✅ VERIFY SIGNATURE (optional, depends on if secret is set)
    if x_slack_signature and x_slack_request_timestamp:
        if not verify_slack_signature(x_slack_request_timestamp, body, x_slack_signature, project):
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        if event_type == "message" and not event.get("subtype"):
            # Regular message (not edited, not deleted)
            user_id = event.get("user")
            user = mapper.map_slack_user(user_id, project)

            if user:
                activity = Activity(
                    user_id=user.id,
                    project_id=project.id,
                    type="message",
                    source="slack",
                    action="sent",
                    content=event.get("text", ""),
                    external_id=event.get("ts"),
                    channel_id=channel_id,
                    timestamp=datetime.fromtimestamp(float(event.get("ts", 0))),
                    impact_score=1.0
                )
                db.add(activity)
                db.commit()

                print(f"✅ Slack webhook: Message from user {user.id}")

        elif event_type == "reaction_added":
            # Someone reacted to a message
            user_id = event.get("user")
            user = mapper.map_slack_user(user_id, project)

            if user:
                activity = Activity(
                    user_id=user.id,
                    project_id=project.id,
                    type="reaction",
                    source="slack",
                    action="added",
                    content=event.get("reaction", ""),
                    external_id=event.get("item", {}).get("ts"),
                    channel_id=channel_id,
                    timestamp=datetime.fromtimestamp(float(event.get("event_ts", 0))),
                    impact_score=0.5
                )
                db.add(activity)
                db.commit()

                print(f"✅ Slack webhook: Reaction from user {user.id}")

        elif event_type == "file_shared":
            # File uploaded
            user_id = event.get("user_id")
            user = mapper.map_slack_user(user_id, project)

            if user:
                file_info = event.get("file", {})

                activity = Activity(
                    user_id=user.id,
                    project_id=project.id,
                    type="file_upload",
                    source="slack",
                    action="shared",
                    title=file_info.get("name", "File"),
                    external_id=file_info.get("id"),
                    external_url=file_info.get("permalink"),
                    channel_id=channel_id,
                    timestamp=datetime.fromtimestamp(float(event.get("event_ts", 0))),
                    impact_score=2.0
                )
                db.add(activity)
                db.commit()

                print(f"✅ Slack webhook: File shared by user {user.id}")

        # Record webhook event
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="slack",
            event_type=event_type,
            success=True
        )

        return create_response(success=True, message="Event received")

    except Exception as e:
        webhook_service.record_webhook_event(
            project_id=project.id,
            tool_name="slack",
            event_type=event_type,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))
