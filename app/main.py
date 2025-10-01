from fastapi import FastAPI
from app.core.database import Base, engine

# Import all models to ensure tables are created

from app.api.v1 import users as users_router
from app.api.v1 import organizations as organizations_router
from app.api.v1 import auth as auth_router
from app.api.v1 import projects as projects_router
from app.api.v1 import tasks as tasks_router
from app.api.v1 import dashboard as dashboard_router
from app.api.v1 import integrations as integrations_router

# Logger setup
import logging
from pythonjsonlogger import jsonlogger

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Teamiq Backend")

# Mount routers under /api/v1
app.include_router(auth_router.router, prefix="/api/v1/auth", tags = ["auth"])
app.include_router(users_router.router, prefix="/api/v1/users", tags = ["users"])
app.include_router(organizations_router.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(projects_router.router, prefix="/api/v1")
app.include_router(tasks_router.router, prefix="/api/v1")
app.include_router(dashboard_router.router, prefix="/api/v1")
app.include_router(integrations_router.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to Teamiq Backend"}





logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)
logHandler = logging.FileHandler("logs/app_logger.log")
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
