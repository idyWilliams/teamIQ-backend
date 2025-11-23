"""
Bidirectional Sync Service
Syncs tasks between TeamIQ and external tools (Jira, ClickUp, Linear)
Handles both pull (external → TeamIQ) and push (TeamIQ → external)
"""

import base64
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import requests
from datetime import datetime
from app.models.project import Project, IntegrationMethod
from app.models.task import Task, TaskStatus, TaskHistory
from app.models.user import User


class IntegrationError(Exception):
    """Custom exception for integration errors"""
    pass


# ==============================================================================
# BASE BIDIRECTIONAL SYNC CLASS
# ==============================================================================

class BaseBidirectionalSync:
    """Base class for bidirectional sync with external tools"""

    def __init__(self, resource, db: Session):
        self.resource = resource
        self.project = resource.project
        self.db = db

    def is_configured(self) -> bool:
        raise NotImplementedError

    def pull_tasks(self) -> List[Task]:
        """Pull tasks FROM external tool TO TeamIQ"""
        raise NotImplementedError

    def push_task_update(self, task: Task) -> bool:
        """Push task changes FROM TeamIQ TO external tool"""
        raise NotImplementedError

    def create_external_task(self, task: Task) -> str:
        """Create new task in external tool"""
        raise NotImplementedError


# ==============================================================================
# JIRA BIDIRECTIONAL SYNC
# ==============================================================================

class JiraBidirectionalSync(BaseBidirectionalSync):
    """Complete Jira integration with bidirectional sync"""

    def is_configured(self) -> bool:
        return bool(
            self.resource.connection.provider == "jira" and
            self.resource.connection.access_token and
            self.resource.resource_id
        )

    def get_headers(self) -> Dict:
        """Build Jira auth headers"""
        token = self.resource.connection.access_token
        return {"Authorization": f"Bearer {token}"}

    def get_api_url(self) -> str:
        """Get Jira API base URL"""
        site_id = self.resource.metadata.get("site_id")
        if not site_id:
             raise IntegrationError("Missing Jira site ID in resource metadata")
        return f"https://api.atlassian.com/ex/jira/{site_id}/rest/api/3"

    # -------------------------------------------------------------------------
    # PULL: External → TeamIQ
    # -------------------------------------------------------------------------

    def pull_tasks(self) -> List[Task]:
        """Pull tasks from Jira to TeamIQ database"""
        if not self.is_configured():
            raise IntegrationError("Jira integration not configured")

        api_url = self.get_api_url()
        headers = self.get_headers()

        try:
            response = requests.get(
                f"{api_url}/search",
                headers=headers,
                params={
                    "jql": f"project={self.resource.resource_id}",
                    "maxResults": 100,
                    "fields": "summary,description,status,assignee,duedate,priority,updated,created"
                },
                timeout=30
            )

            if response.status_code != 200:
                raise IntegrationError(f"Jira API error: {response.status_code}")

            issues = response.json().get("issues", [])
            synced_tasks = []

            for issue in issues:
                task = self._sync_jira_issue_to_task(issue)
                synced_tasks.append(task)

            self.db.commit()
            print(f"✅ Pulled {len(synced_tasks)} tasks from Jira")
            return synced_tasks

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to Jira: {str(e)}")

    def _sync_jira_issue_to_task(self, issue: Dict) -> Task:
        """Convert Jira issue to TeamIQ task"""
        issue_id = issue["id"]
        issue_key = issue["key"]
        fields = issue["fields"]

        # Find or create task
        task = self.db.query(Task).filter(
            Task.external_id == issue_id,
            Task.external_source == "jira"
        ).first()

        if not task:
            task = Task(
                external_id=issue_id,
                external_source="jira",
                project_id=self.project.id,
                organization_id=self.project.organization_id
            )
            self.db.add(task)

        # Update task fields
        old_status = task.status.value if task.status else None

        task.title = fields["summary"]
        task.description = fields.get("description", "")
        task.status = self._map_jira_status(fields["status"]["name"])
        task.external_status = fields["status"]["name"]
        task.due_date = fields.get("duedate")
        task.last_synced_at = datetime.utcnow()
        # Construct URL from metadata if available
        base_url = self.resource.metadata.get("url", "")
        task.external_url = f"{base_url}/browse/{issue_key}" if base_url else ""

        # Map assignee
        assignee = fields.get("assignee")
        if assignee and assignee.get("emailAddress"):
            user = self.db.query(User).filter(
                User.email == assignee["emailAddress"]
            ).first()
            if user:
                task.owner_id = user.id

        # Track status change
        new_status = task.status.value
        if old_status and old_status != new_status:
            self._log_status_change(task, old_status, new_status, "jira")

        return task

    # -------------------------------------------------------------------------
    # PUSH: TeamIQ → External
    # -------------------------------------------------------------------------

    def push_task_update(self, task: Task) -> bool:
        """Push task changes from TeamIQ to Jira"""
        if not self.is_configured():
            return False

        if not task.external_id:
            # Task doesn't exist in Jira yet - create it
            return self.create_external_task(task)

        api_url = self.get_api_url()
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        # Build update payload
        update_data = {
            "fields": {
                "summary": task.title,
                "description": task.description or "",
            }
        }

        # Update status if changed
        if task.status:
            jira_status = self._map_teamiq_to_jira_status(task.status)
            update_data["transition"] = {"id": jira_status}

        try:
            response = requests.put(
                f"{api_url}/issue/{task.external_id}",
                headers=headers,
                json=update_data,
                timeout=30
            )

            if response.status_code in [200, 204]:
                task.last_synced_at = datetime.utcnow()
                self.db.commit()
                print(f"✅ Pushed task {task.id} to Jira")
                return True
            else:
                print(f"❌ Failed to push to Jira: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error pushing to Jira: {str(e)}")
            return False

    def create_external_task(self, task: Task) -> str:
        """Create new task in Jira"""
        api_url = self.get_api_url()
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "fields": {
                "project": {"key": self.resource.resource_id},
                "summary": task.title,
                "description": task.description or "",
                "issuetype": {"name": "Task"}
            }
        }

        try:
            response = requests.post(
                f"{api_url}/issue",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                issue = response.json()
                task.external_id = issue["id"]
                task.external_source = "jira"
                base_url = self.resource.metadata.get("url", "")
                task.external_url = f"{base_url}/browse/{issue['key']}" if base_url else ""
                task.last_synced_at = datetime.utcnow()
                self.db.commit()
                print(f"✅ Created task in Jira: {issue['key']}")
                return issue["id"]
            else:
                raise IntegrationError(f"Failed to create Jira task: {response.status_code}")

        except Exception as e:
            raise IntegrationError(f"Error creating Jira task: {str(e)}")

    # -------------------------------------------------------------------------
    # Status Mapping
    # -------------------------------------------------------------------------

    def _map_jira_status(self, jira_status: str) -> TaskStatus:
        """Map Jira status to TeamIQ status"""
        status_map = {
            "to do": TaskStatus.TODO,
            "backlog": TaskStatus.BACKLOG,
            "in progress": TaskStatus.IN_PROGRESS,
            "done": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
        }
        return status_map.get(jira_status.lower(), TaskStatus.TODO)

    def _map_teamiq_to_jira_status(self, teamiq_status: TaskStatus) -> str:
        """Map TeamIQ status to Jira transition ID"""
        # Note: Jira uses transition IDs, not status names
        # These are typical IDs, but may vary by Jira instance
        status_map = {
            TaskStatus.TODO: "11",  # To Do
            TaskStatus.BACKLOG: "21",  # Backlog
            TaskStatus.IN_PROGRESS: "31",  # In Progress
            TaskStatus.DONE: "41",  # Done
        }
        return status_map.get(teamiq_status, "11")

    def _log_status_change(self, task: Task, old_status: str, new_status: str, source: str):
        """Log task status change for history tracking"""
        history = TaskHistory(
            task_id=task.id,
            field_name="status",
            old_value=old_status,
            new_value=new_status,
            source=source
        )
        self.db.add(history)


# ==============================================================================
# CLICKUP BIDIRECTIONAL SYNC
# ==============================================================================

class ClickUpBidirectionalSync(BaseBidirectionalSync):
    """Complete ClickUp integration with bidirectional sync"""

    def is_configured(self) -> bool:
        return bool(
            self.resource.connection.provider == "clickup" and
            self.resource.resource_id and
            self.resource.connection.api_key
        )

   # In bidirectional_sync.py

    def get_headers(self) -> Dict:
        """Build ClickUp auth headers"""
        return {"Authorization": self.resource.connection.api_key}


    # -------------------------------------------------------------------------
    # PULL: External → TeamIQ
    # -------------------------------------------------------------------------

    def pull_tasks(self) -> List[Task]:
        """Pull tasks from ClickUp"""
        headers = self.get_headers()

        try:
            response = requests.get(
                f"https://api.clickup.com/api/v2/list/{self.resource.resource_id}/task",
                headers=headers,
                params={"include_closed": "true"},
                timeout=30
            )

            if response.status_code != 200:
                raise IntegrationError(f"ClickUp API error: {response.status_code}")

            tasks_data = response.json().get("tasks", [])
            synced_tasks = []

            for task_data in tasks_data:
                task = self._sync_clickup_task(task_data)
                synced_tasks.append(task)

            self.db.commit()
            print(f"✅ Pulled {len(synced_tasks)} tasks from ClickUp")
            return synced_tasks

        except requests.exceptions.RequestException as e:
            raise IntegrationError(f"Failed to connect to ClickUp: {str(e)}")

    def _sync_clickup_task(self, task_data: Dict) -> Task:
        """Convert ClickUp task to TeamIQ task"""
        task_id = task_data["id"]

        # Find or create task
        task = self.db.query(Task).filter(
            Task.external_id == task_id,
            Task.external_source == "clickup"
        ).first()

        if not task:
            task = Task(
                external_id=task_id,
                external_source="clickup",
                project_id=self.project.id,
                organization_id=self.project.organization_id
            )
            self.db.add(task)

        # Update task fields
        task.title = task_data["name"]
        task.description = task_data.get("description", "")
        task.status = self._map_clickup_status(task_data["status"]["status"])
        task.external_status = task_data["status"]["status"]
        task.due_date = task_data.get("due_date")
        task.last_synced_at = datetime.utcnow()
        task.external_url = task_data["url"]

        # Map assignee
        assignees = task_data.get("assignees", [])
        if assignees:
            email = assignees[0].get("email")
            if email:
                user = self.db.query(User).filter(User.email == email).first()
                if user:
                    task.owner_id = user.id

        return task

    # -------------------------------------------------------------------------
    # PUSH: TeamIQ → External
    # -------------------------------------------------------------------------

    def push_task_update(self, task: Task) -> bool:
        """Push task changes to ClickUp"""
        if not task.external_id:
            return self.create_external_task(task)

        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        update_data = {
            "name": task.title,
            "description": task.description or "",
            "status": self._map_teamiq_to_clickup_status(task.status)
        }

        try:
            response = requests.put(
                f"https://api.clickup.com/api/v2/task/{task.external_id}",
                headers=headers,
                json=update_data,
                timeout=30
            )

            if response.status_code == 200:
                task.last_synced_at = datetime.utcnow()
                self.db.commit()
                print(f"✅ Pushed task {task.id} to ClickUp")
                return True
            return False

        except Exception as e:
            print(f"❌ Error pushing to ClickUp: {str(e)}")
            return False

    def create_external_task(self, task: Task) -> str:
        """Create new task in ClickUp"""
        headers = self.get_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "name": task.title,
            "description": task.description or "",
            "status": self._map_teamiq_to_clickup_status(task.status)
        }

        try:
            response = requests.post(
                f"https://api.clickup.com/api/v2/list/{self.resource.resource_id}/task",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                task_data = response.json()
                task.external_id = task_data["id"]
                task.external_source = "clickup"
                task.external_url = task_data["url"]
                task.last_synced_at = datetime.utcnow()
                self.db.commit()
                return task_data["id"]

        except Exception as e:
            raise IntegrationError(f"Error creating ClickUp task: {str(e)}")

    def _map_clickup_status(self, clickup_status: str) -> TaskStatus:
        """Map ClickUp status to TeamIQ"""
        status_map = {
            "to do": TaskStatus.TODO,
            "in progress": TaskStatus.IN_PROGRESS,
            "complete": TaskStatus.DONE,
            "closed": TaskStatus.DONE,
        }
        return status_map.get(clickup_status.lower(), TaskStatus.TODO)

    def _map_teamiq_to_clickup_status(self, teamiq_status: TaskStatus) -> str:
        """Map TeamIQ status to ClickUp"""
        status_map = {
            TaskStatus.BACKLOG: "to do",
            TaskStatus.TODO: "to do",
            TaskStatus.IN_PROGRESS: "in progress",
            TaskStatus.DONE: "complete",
        }
        return status_map.get(teamiq_status, "to do")


# ==============================================================================
# SYNC FACTORY
# ==============================================================================

def get_sync_services(project: Project, db: Session) -> List[BaseBidirectionalSync]:
    """Factory to get all appropriate sync services based on project resources"""
    services = []

    # Iterate over project resources
    # We need to make sure resources are loaded.
    # If project is passed from a query that didn't eager load, this might trigger a lazy load.

    pm_providers = ["jira", "clickup", "linear"]

    for resource in project.resources:
        if resource.connection.provider in pm_providers:
            if resource.connection.provider == "jira":
                services.append(JiraBidirectionalSync(resource, db))
            elif resource.connection.provider == "clickup":
                services.append(ClickUpBidirectionalSync(resource, db))
            # elif resource.connection.provider == "linear":
            #     services.append(LinearBidirectionalSync(resource, db))

    return services


