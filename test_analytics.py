import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

from app.services.analytics_service import AnalyticsService

try:
    service = AnalyticsService(session)
    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)
    last_month = now - timedelta(days=30)
    
    velocity = service._calculate_velocity(project_id=9, last_week=last_week, last_month=last_month)
    print("Velocity calculated successfully:", velocity)
except Exception as e:
    import traceback
    traceback.print_exc()

