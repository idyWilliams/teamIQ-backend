from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.schemas.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskMoveRequest,
    TaskWithHistory
)
from app.repositories import task_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.organization import Organization
from app.models.project import Project
from app.services.bidirectional_sync import get_sync_services

router = APIRouter()


# ==============================================================================
# CREATE TASK (with optional sync to external tool)
# ==============================================================================

@router.post("/", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Create new task in TeamIQ and optionally sync to external tool
    """
    # Determine user/org
    if isinstance(current_user, User):
        user_id = current_user.id
        org_id = current_user.organizations[0].id if current_user.organizations else None
    else:  # Organization
        user_id = None
        org_id = current_user.id

    # Create task in database
    db_task = task_repository.create_task(
        db=db,
        task=task_data,
        user_id=task_data.owner_id or user_id,
        org_id=org_id
    )

    # If task belongs to a project with PM tool integration, create in external tool
    if db_task.project_id:
        project = db.query(Project).filter(Project.id == db_task.project_id).first()
        if project and project.pm_tool:
            sync_services = get_sync_services(project, db)
            if sync_services:
                # Use the first PM sync service for task creation
                background_tasks.add_task(sync_services[0].create_external_task, db_task)

    return create_response(
        success=True,
        message="Task created successfully",
        data=TaskResponse.model_validate(db_task)
    )


# ==============================================================================
# GET TASKS (with filtering and sync status)
# ==============================================================================

@router.get("/", response_model=List[TaskResponse])
def get_tasks(
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    skip: int = 0,
    limit: int = 100,
    include_external: bool = True,  # Include tasks from external tools
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Get all tasks for current user/organization
    Optionally filtered by project and status
    """
    if isinstance(current_user, User):
        user_id = current_user.id
        org_id = current_user.organizations[0].id if current_user.organizations else None
    else:
        user_id = None
        org_id = current_user.id

    # Build query
    query = db.query(Task)

    if user_id:
        query = query.filter(Task.owner_id == user_id)
    elif org_id:
        query = query.filter(Task.organization_id == org_id)

    if project_id:
        query = query.filter(Task.project_id == project_id)

    if status:
        query = query.filter(Task.status == status)

    tasks = query.offset(skip).limit(limit).all()

    return create_response(
        success=True,
        message=f"Retrieved {len(tasks)} tasks",
        data=[TaskResponse.model_validate(t) for t in tasks]
    )


# ==============================================================================
# GET SINGLE TASK (with history)
# ==============================================================================

@router.get("/{task_id}", response_model=TaskWithHistory)
def get_task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Get detailed task information with change history"""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorization check
    if isinstance(current_user, User):
        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if task.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Build response with history
    task_dict = TaskResponse.model_validate(task).model_dump()
    task_dict["history"] = [
        {
            "field": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "source": h.source,
            "timestamp": h.timestamp.isoformat()
        }
        for h in task.history
    ]
    task_dict["comments"] = [
        {
            "id": c.id,
            "user_id": c.user_id,
            "content": c.content,
            "created_at": c.createdAt.isoformat()
        }
        for c in task.comments
    ]

    return create_response(
        success=True,
        message="Task retrieved successfully",
        data=task_dict
    )


# ==============================================================================
# UPDATE TASK (with sync to external tool)
# ==============================================================================

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Update task and sync changes to external tool
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorization check
    if isinstance(current_user, User):
        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if task.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Update task
    updated_task = task_repository.update_task(db, task_id, task_update)

    # Sync to external tool if integrated
    if task.project_id and task.external_source:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project:
            sync_services = get_sync_services(project, db)
            if sync_services:
                background_tasks.add_task(sync_services[0].push_task_update, updated_task)

    return create_response(
        success=True,
        message="Task updated successfully",
        data=TaskResponse.model_validate(updated_task)
    )


# ==============================================================================
# MOVE TASK (Kanban drag-drop with sync)
# ==============================================================================

@router.post("/{task_id}/move", response_model=TaskResponse)
def move_task(
    task_id: int,
    move_request: TaskMoveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Move task to different status column (Kanban board drag-drop)
    Syncs to Jira/ClickUp automatically
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorization check
    if isinstance(current_user, User):
        if task.owner_id != current_user.id:
            user_org_ids = [org.id for org in current_user.organizations]
            if task.organization_id not in user_org_ids:
                raise HTTPException(status_code=403, detail="Not authorized")

    # Update status
    old_status = task.status
    task.status = move_request.new_status

    # Mark as completed if moved to DONE
    if move_request.new_status == TaskStatus.DONE and not task.completed_at:
        task.completed_at = datetime.utcnow()
    elif move_request.new_status != TaskStatus.DONE:
        task.completed_at = None

    # Log history
    from app.models.task import TaskHistory
    history = TaskHistory(
        task_id=task.id,
        user_id=current_user.id if isinstance(current_user, User) else None,
        field_name="status",
        old_value=old_status.value,
        new_value=move_request.new_status.value,
        source="teamiq"
    )
    db.add(history)
    db.commit()
    db.refresh(task)

    # Sync to external tool
    if task.project_id and task.external_source:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project:
            sync_services = get_sync_services(project, db)
            if sync_services:
                background_tasks.add_task(sync_services[0].push_task_update, task)

    return create_response(
        success=True,
        message=f"Task moved to {move_request.new_status.value}",
        data=TaskResponse.model_validate(task)
    )


# ==============================================================================
# SYNC TASKS FROM EXTERNAL TOOL
# ==============================================================================

@router.post("/sync/pull")
def pull_tasks_from_external(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """
    Manually pull all tasks from external tool (Jira/ClickUp)
    """
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Authorization check
    if isinstance(current_user, User):
        user_org_ids = [org.id for org in current_user.organizations]
        if project.organization_id not in user_org_ids:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if project.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Get sync service
    sync_services = get_sync_services(project, db)

    if not sync_services:
        raise HTTPException(
            status_code=400,
            detail=f"No sync service available for {project.pm_tool}"
        )

    try:
        synced_tasks = sync_services[0].pull_tasks()
        return create_response(
            success=True,
            message=f"Successfully synced {len(synced_tasks)} tasks from {project.pm_tool}",
            data={
                "synced_count": len(synced_tasks),
                "project_id": project_id,
                "source": project.pm_tool
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync tasks: {str(e)}"
        )


# ==============================================================================
# DELETE TASK
# ==============================================================================

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_or_organization)
):
    """Delete task (only from TeamIQ, not from external tool)"""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Authorization check
    if isinstance(current_user, User):
        if task.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    elif isinstance(current_user, Organization):
        if task.organization_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(task)
    db.commit()

    return create_response(
        success=True,
        message="Task deleted successfully",
        data={"task_id": task_id}
    )
