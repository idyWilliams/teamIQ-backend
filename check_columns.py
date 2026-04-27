#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

try:
    inspector = inspect(engine)
    columns = inspector.get_columns('user_organizations')
    print("Columns in user_organizations table:")
    for column in columns:
        print(f"- {column['name']} ({column['type']})")

except Exception as e:
    print(f"Error: {e}")
