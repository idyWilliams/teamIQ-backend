from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
from app.core.database import Base, engine

# Import all route modules
from app.api.v1 import (
    auth,
    users,
    organizations,
    projects,
    tasks,
    dashboard,
    integrations,
    invitations,
    skills,
    notifications,
    upload
)

# Logger setup
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("app_logger")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logHandler = logging.FileHandler(LOG_DIR / "app_logger.log")
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)

# Initialize FastAPI app
app = FastAPI(
    title="TeamIQ Backend",
    description="Backend API for TeamIQ Project Management Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "https://team-iq-frontend.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
@app.on_event("startup")
def on_startup():
    """Create database tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables on startup: {e}")

# Root
@app.get("/", tags=["Health"])
def root():
    """Root endpoint - Health check"""
    return {
        "status": "healthy",
        "message": "TeamIQ Backend API is running",
        "version": "1.0.0"
    }

# Test
@app.get("/test-cors", tags=["Health"])
def test_cors():
    """Test CORS configuration"""
    return {"message": "CORS test successful"}

# Include all routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(integrations.router, prefix="/api/v1/integrations", tags=["Integrations"])
app.include_router(invitations.router, prefix="/api/v1/invitations", tags=["Invitations"])
app.include_router(skills.router, prefix="/api/v1/skills", tags=["Skills"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(upload.router, prefix="/api/v1", tags=["Upload"])

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to catch all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An unexpected internal server error occurred.",
            "error_type": type(exc).__name__,
            "error_details": str(exc)
        }
    )
