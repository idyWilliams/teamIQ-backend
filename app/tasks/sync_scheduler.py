"""
Background Scheduler for Integration Syncing
Runs periodic syncs for all project integrations
"""

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.core.database import SessionLocal
from app.models.project import Project
from app.services.integration_sync import sync_project_integrations

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def sync_all_projects():
    """
    Sync integrations for ALL projects in database
    Runs automatically on schedule
    """
    db: Session = SessionLocal()

    try:
        # Get all projects that have at least one integration configured
        # Check both legacy columns and new resources
        from app.models.project_resource import ProjectResource

        projects = db.query(Project).outerjoin(ProjectResource).filter(
            (Project.pm_tool.isnot(None)) |
            (Project.vc_tool.isnot(None)) |
            (Project.comm_tool.isnot(None)) |
            (ProjectResource.id.isnot(None))
        ).distinct().all()

        if not projects:
            logger.info("No projects with integrations configured")
            return

        logger.info(f"🚀 Starting sync for {len(projects)} projects at {datetime.now()}")

        success_count = 0
        error_count = 0

        for project in projects:
            try:
                results = sync_project_integrations(project.id, db)

                # Check if sync was successful
                has_error = any("error" in str(v) for v in results.values())
                if has_error:
                    error_count += 1
                    logger.warning(f"⚠️  Project {project.id} sync had errors: {results}")
                else:
                    success_count += 1
                    logger.info(f"✅ Project {project.id} synced successfully")

            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error syncing project {project.id}: {str(e)}")

        logger.info(
            f"✅ Sync complete at {datetime.now()}. "
            f"Success: {success_count}, Errors: {error_count}"
        )

    except Exception as e:
        logger.error(f"❌ Critical error in sync_all_projects: {str(e)}")

    finally:
        db.close()


def sync_single_project(project_id: int):
    """
    Sync a single project immediately (called on-demand)
    """
    db: Session = SessionLocal()

    try:
        logger.info(f"🔄 Starting on-demand sync for project {project_id}")
        results = sync_project_integrations(project_id, db)
        logger.info(f"✅ On-demand sync complete for project {project_id}: {results}")
        return results

    except Exception as e:
        logger.error(f"❌ Error in on-demand sync for project {project_id}: {str(e)}")
        return {"error": str(e)}

    finally:
        db.close()


# Initialize the scheduler
scheduler = BackgroundScheduler()

# Schedule automatic syncs
# Option 1: Run every 15 minutes
scheduler.add_job(
    sync_all_projects,
    'interval',
    minutes=15,
    id='sync_all_projects_interval',
    name='Sync all project integrations every 15 minutes',
    replace_existing=True
)

# Option 2: Run at specific times (uncomment to use instead)
# scheduler.add_job(
#     sync_all_projects,
#     CronTrigger(hour='*/2'),  # Every 2 hours
#     id='sync_all_projects_cron',
#     name='Sync all project integrations every 2 hours',
#     replace_existing=True
# )

# Option 3: Run multiple times per day (uncomment to use)
# scheduler.add_job(
#     sync_all_projects,
#     CronTrigger(hour='9,12,15,18'),  # At 9am, 12pm, 3pm, 6pm
#     id='sync_all_projects_daily',
#     name='Sync all project integrations 4 times daily',
#     replace_existing=True
# )


def start_scheduler():
    """Start the background scheduler"""
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ Integration sync scheduler started")
    else:
        logger.info("ℹ️  Scheduler already running")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 Integration sync scheduler stopped")


def get_scheduler_status():
    """Get current scheduler status and jobs"""
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ]
    }
