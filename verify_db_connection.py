import sys
import os
from sqlalchemy import text

# Add the current directory to sys.path to make app importable
sys.path.append(os.getcwd())

try:
    from app.core.database import engine

    print("Attempting to connect to the database...")
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(f"Connection successful! Result: {result.scalar()}")

except Exception as e:
    print(f"Connection failed: {e}")
    sys.exit(1)
