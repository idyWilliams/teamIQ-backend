from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import logging
from pythonjsonlogger import jsonlogger
from app.core.database import Base, engine
from app.schemas.response_model import create_response

# ----------------------------------------
# Logger setup
# ----------------------------------------
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logHandler = logging.FileHandler(LOG_DIR / "app_logger.log")
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# ----------------------------------------
# Database table creation
# ----------------------------------------
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error(f"Error creating tables: {e}")

# ----------------------------------------
# App setup
# ----------------------------------------
app = FastAPI(title="Teamiq Backend")

# Import routers
from app.api.v1 import (
    auth, users, organizations, projects, tasks, dashboard,
    integrations, invitations, skills, notifications
)

# Include routers
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

# ----------------------------------------
# Exception handler
# ----------------------------------------
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    user_message = "An unexpected error occurred."
    troubleshooting_steps = "Please try again later or contact support if the problem persists."

    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        user_message = exc.detail or user_message
    else:
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content=create_response(
            success=False,
            message=user_message,
            errors={"details": str(exc), "troubleshooting": troubleshooting_steps},
        ).model_dump(),
    )

# ----------------------------------------
# Root route
# ----------------------------------------
@app.get("/")
def root():
    return {"message": "Welcome to Teamiq Backend"}
