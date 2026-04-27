#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def add_column_if_not_exists():
    inspector = inspect(engine)
    columns = [c['name'] for c in inspector.get_columns('project_members')]

    if 'external_mappings' not in columns:
        print("Adding external_mappings column to project_members table...")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE project_members ADD COLUMN external_mappings JSON"))
            conn.commit()
        print("✅ Column added successfully.")
    else:
        print("✅ external_mappings column already exists.")

if __name__ == "__main__":
    try:
        add_column_if_not_exists()
    except Exception as e:
        print(f"Error: {e}")
