import sys
import os
from sqlalchemy import create_engine, text

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from app.core.database import engine

def add_column():
    print("Adding 'files' column to commit_activities table...")
    try:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE commit_activities ADD COLUMN files JSON"))
            connection.commit()
        print("✅ Successfully added 'files' column")
    except Exception as e:
        if "already exists" in str(e):
            print("⚠️ Column 'files' already exists")
        else:
            print(f"❌ Error adding column: {e}")

if __name__ == "__main__":
    add_column()
