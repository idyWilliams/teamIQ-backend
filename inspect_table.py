#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

try:
    inspector = inspect(engine)
    table_name = sys.argv[1] if len(sys.argv) > 1 else 'tasks'
    columns = inspector.get_columns(table_name)
    print(f"Columns in {table_name} table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")

except Exception as e:
    print(f"Error: {e}")
