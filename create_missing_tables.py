import sys
import os
from sqlalchemy import create_engine

# Add the current directory to sys.path so we can import app modules
sys.path.append(os.getcwd())

from app.core.database import Base, engine
from app.models.project_resource import ProjectResource
from app.models.project import Project
from app.models.integration import IntegrationConnection

def create_tables():
    print("Creating missing tables...")
    try:
        # This will create any tables that are defined in metadata but missing in DB
        Base.metadata.create_all(bind=engine)
        print("✅ Successfully created missing tables (including project_resources)")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    create_tables()
