import sys
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

from app.tasks.sync_scheduler import sync_single_project

print("Running sync for project 9...")
try:
    results = sync_single_project(9)
    print("Sync results:", results)
except Exception as e:
    import traceback
    traceback.print_exc()

