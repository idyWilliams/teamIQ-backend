from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pathlib import Path
from app.core.database import Base, engine
from app.schemas.response_model import create_response, APIResponse
from fastapi import HTTPException
import datetime

# Import models for table creation
from app.models.user import User
from app.models.organization import Organization
from app.models.task import Task
from app.models.project import Project
from app.models.invitation import Invitation
from app.models.integration import LinkedAccount  # Note: filename is integration.py, but import as integration
from app.models.dashboard import DashboardMetrics, OrgDashboardMetrics
from app.models.skill import Skill, UserSkill
from app.models.notification import Notification

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Teamiq Backend")

# Routers (adjusted for app/api/v1/ path)
from app.api.v1 import (
    auth, users, organizations, projects, tasks, dashboard,
    integrations, invitations, skills, notifications
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(invitations.router, prefix="/api/v1/invitations", tags=["invitations"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=create_response(
            success=False,
            message=exc.detail,
            errors={"status_code": exc.status_code},
        ).model_dump(),
    )

@app.get("/")
def root():
    return {"message": "Welcome to Teamiq Backend"}