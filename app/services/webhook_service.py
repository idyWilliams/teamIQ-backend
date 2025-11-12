"""
Webhook Persistence & Health Monitoring
Ensures webhooks work forever, across sessions
"""

from sqlalchemy.orm import Session
from app.models.webhook import WebhookStatus
from app.models.project import Project
from datetime import datetime
from typing import Dict


class WebhookPersistenceService:
    """Manages webhook lifecycle and persistence"""

    def __init__(self, db: Session):
        self.db = db

    def initialize_webhooks_for_project(self, project_id: int):
        """
        Initialize webhook tracking when project is created (Step 5)
        Called automatically after Step 5 completion
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()

        if not project:
            return

        webhooks_to_create = []

        # PM Tool webhook
        if project.pm_tool:
            webhooks_to_create.append({
                "project_id": project_id,
                "tool_type": "pm_tool",
                "tool_name": project.pm_tool,
                "webhook_url": f"https://teamiq.com/api/v1/webhooks/{project.pm_tool}",
                "is_configured": False  # User hasn't set it up in external tool yet
            })

        # Version Control webhook
        if project.vc_tool:
            webhooks_to_create.append({
                "project_id": project_id,
                "tool_type": "vc_tool",
                "tool_name": project.vc_tool,
                "webhook_url": f"https://teamiq.com/api/v1/webhooks/{project.vc_tool}",
                "is_configured": False
            })

        # Communication webhook
        if project.comm_tool:
            endpoint = "slack/events" if project.comm_tool == "slack" else project.comm_tool
            webhooks_to_create.append({
                "project_id": project_id,
                "tool_type": "comm_tool",
                "tool_name": project.comm_tool,
                "webhook_url": f"https://teamiq.com/api/v1/webhooks/{endpoint}",
                "is_configured": False
            })

        # Create webhook status records
        for webhook_data in webhooks_to_create:
            # Check if already exists
            existing = self.db.query(WebhookStatus).filter(
                WebhookStatus.project_id == project_id,
                WebhookStatus.tool_name == webhook_data["tool_name"]
            ).first()

            if not existing:
                webhook_status = WebhookStatus(**webhook_data)
                self.db.add(webhook_status)

        self.db.commit()
        print(f"✅ Initialized {len(webhooks_to_create)} webhooks for project {project_id}")

    def mark_webhook_configured(self, project_id: int, tool_name: str):
        """
        Mark webhook as configured when first event is received
        This happens automatically when external tool sends first webhook
        """
        webhook = self.db.query(WebhookStatus).filter(
            WebhookStatus.project_id == project_id,
            WebhookStatus.tool_name == tool_name
        ).first()

        if webhook and not webhook.is_configured:
            webhook.is_configured = True
            webhook.last_verified_at = datetime.utcnow()
            self.db.commit()
            print(f"✅ Webhook configured: {tool_name} for project {project_id}")

    def record_webhook_event(
        self,
        project_id: int,
        tool_name: str,
        event_type: str,
        success: bool = True,
        error: str = None
    ):
        """
        Record webhook event delivery
        Called every time a webhook is received
        """
        webhook = self.db.query(WebhookStatus).filter(
            WebhookStatus.project_id == project_id,
            WebhookStatus.tool_name == tool_name
        ).first()

        if webhook:
            webhook.total_events_received += 1
            webhook.last_event_received_at = datetime.utcnow()
            webhook.last_event_type = event_type

            # Mark as configured on first successful event
            if success and not webhook.is_configured:
                webhook.is_configured = True
                webhook.last_verified_at = datetime.utcnow()

            # Track errors
            if not success:
                webhook.failed_deliveries += 1
                webhook.last_error = error
                webhook.last_error_at = datetime.utcnow()

            self.db.commit()

    def get_webhook_health(self, project_id: int) -> Dict:
        """
        Get health status of all webhooks for a project
        Used in dashboard to show webhook status
        """
        webhooks = self.db.query(WebhookStatus).filter(
            WebhookStatus.project_id == project_id
        ).all()

        health = {
            "total_webhooks": len(webhooks),
            "configured_webhooks": sum(1 for w in webhooks if w.is_configured),
            "pending_setup": sum(1 for w in webhooks if not w.is_configured),
            "webhooks": []
        }

        for webhook in webhooks:
            # Determine health status
            if not webhook.is_configured:
                status = "pending"
            elif webhook.last_event_received_at:
                # Check if webhook is active (received event in last 24 hours)
                time_since_last_event = (datetime.utcnow() - webhook.last_event_received_at).total_seconds() / 3600
                if time_since_last_event < 24:
                    status = "active"
                elif time_since_last_event < 168:  # 7 days
                    status = "idle"
                else:
                    status = "inactive"
            else:
                status = "configured_but_no_events"

            health["webhooks"].append({
                "tool_name": webhook.tool_name,
                "tool_type": webhook.tool_type,
                "status": status,
                "is_configured": webhook.is_configured,
                "total_events": webhook.total_events_received,
                "last_event_at": webhook.last_event_received_at.isoformat() if webhook.last_event_received_at else None,
                "failed_deliveries": webhook.failed_deliveries,
                "webhook_url": webhook.webhook_url
            })

        return health


def get_webhook_service(db: Session) -> WebhookPersistenceService:
    """Factory function to get webhook service"""
    return WebhookPersistenceService(db)
