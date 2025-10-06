# app/main.py
from fastapi import FastAPI
from pathlib import Path
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

# OpenAPI helper
from fastapi.openapi.utils import get_openapi

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Teamiq Backend")

# -------------------------
# Custom OpenAPI schema
# -------------------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add custom security schemes for individual and organization login tokens
    openapi_schema.setdefault("components", {})
    openapi_schema["components"].setdefault("securitySchemes", {})

    openapi_schema["components"]["securitySchemes"].update(
        {
            "oauth2_individual": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "/api/v1/auth/login/individual",
                        "scopes": {"individual": "Individual access"},
                    }
                },
            },
            "oauth2_organization": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "tokenUrl": "/api/v1/auth/login/organization",
                        "scopes": {"organization": "Organization access"},
                    }
                },
            },
        }
    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Set the custom schema on startup
@app.on_event("startup")
def startup_event():
    custom_openapi()

# -------------------------
# Mount routers under /api/v1
# -------------------------
app.include_router(auth_router.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users_router.router, prefix="/api/v1/users", tags=["users"])
app.include_router(organizations_router.router, prefix="/api/v1/organizations", tags=["organizations"])
app.include_router(projects_router.router, prefix="/api/v1")
app.include_router(tasks_router.router, prefix="/api/v1")
app.include_router(dashboard_router.router, prefix="/api/v1")
app.include_router(integrations_router.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to Teamiq Backend"}

# -------------------------
# Logger initialization
# -------------------------
logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Example: file logger with JSON formatter (uncomment to enable)
# logHandler = logging.FileHandler(LOG_DIR / "app_logger.log")
# formatter = jsonlogger.JsonFormatter()
# logHandler.setFormatter(formatter)
# logger.addHandler(logHandler)