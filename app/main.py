from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pathlib import Path
from app.core.database import Base, engine
from app.schemas.response_model import create_response
from fastapi import HTTPException

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

# Import all models to ensure tables are created

from app.api.v1 import (
    auth, users, organizations, projects, tasks, dashboard,
    integrations, invitations, skills, notifications
)

app = FastAPI(title="Teamiq Backend")
