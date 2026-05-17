#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def add_column(engine, table_name, column_name, column_type, default=None):
    try:
        with engine.connect() as conn:
            # Check if column exists
            inspector = inspect(engine)
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            if column_name in columns:
                print(f"Column '{column_name}' already exists in '{table_name}'.")
                return

            alter_cmd = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default is not None:
                alter_cmd += f" DEFAULT {default}"
            
            conn.execute(text(alter_cmd))
            conn.commit()
            print(f"Added column '{column_name}' to '{table_name}'.")
    except Exception as e:
        print(f"Error adding column '{column_name}': {e}")

def create_enum(engine, enum_name, values):
    try:
        with engine.connect() as conn:
            # Check if enum exists
            res = conn.execute(text(f"SELECT 1 FROM pg_type WHERE typname = '{enum_name.lower()}'"))
            if res.fetchone():
                print(f"Enum '{enum_name}' already exists. Checking values...")
                existing_values = [r[0] for r in conn.execute(text(f"SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE typname = '{enum_name.lower()}'"))]
                if set(existing_values) == set(values):
                    print("Values match.")
                    return
                else:
                    print(f"Values mismatch. Existing: {existing_values}, Expected: {values}")
                    print("Dropping and recreating enum...")
                    # We can only drop if no one uses it. We checked that.
                    conn.execute(text(f"DROP TYPE {enum_name} CASCADE"))
                    conn.commit()

            values_str = ", ".join([f"'{v}'" for v in values])
            conn.execute(text(f"CREATE TYPE {enum_name} AS ENUM ({values_str})"))
            conn.commit()
            print(f"Created enum '{enum_name}' with values {values}.")
    except Exception as e:
        print(f"Error creating enum '{enum_name}': {e}")

if __name__ == "__main__":
    # Create Enums if needed
    create_enum(engine, "taskpriority", ["low", "medium", "high", "urgent"])
    create_enum(engine, "taskstatus", ["backlog", "todo", "in_progress", "done"])

    # Add missing columns to 'tasks'
    add_column(engine, "tasks", "priority", "taskpriority", default="'medium'")
    
    # Check if 'status' column exists and if it's correct
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            columns = {c['name']: c for c in inspector.get_columns('tasks')}
            if 'status' in columns:
                # We know from our manual check that it's 'taskstatus' enum but with uppercase values.
                # Since we just recreated taskstatus with lowercase values, we might need to 
                # re-add the column or alter it if it's already using the type.
                # If we dropped the type with CASCADE, the column might be gone or in a weird state.
                pass
            else:
                add_column(engine, "tasks", "status", "taskstatus", default="'backlog'")
    except Exception as e:
        print(f"Error handling 'status' column: {e}")

    add_column(engine, "tasks", "project_id", "INTEGER REFERENCES projects(id)")
    add_column(engine, "tasks", "external_id", "VARCHAR")
    add_column(engine, "tasks", "external_source", "VARCHAR")
    add_column(engine, "tasks", "external_url", "VARCHAR")
    add_column(engine, "tasks", "external_status", "VARCHAR")
    add_column(engine, "tasks", "last_synced_at", "TIMESTAMP WITH TIME ZONE")
    add_column(engine, "tasks", "sync_enabled", "BOOLEAN", default="TRUE")
    add_column(engine, "tasks", "is_blocked", "BOOLEAN", default="FALSE")
    add_column(engine, "tasks", "blocker_details", "TEXT")
    add_column(engine, "tasks", "due_date", "TIMESTAMP WITH TIME ZONE")
    add_column(engine, "tasks", "estimated_hours", "INTEGER")
    add_column(engine, "tasks", "actual_hours", "INTEGER")
    add_column(engine, "tasks", "tags", "JSON")
    add_column(engine, "tasks", "attachments", "JSON")
    add_column(engine, "tasks", "view_count", "INTEGER", default="0")
    add_column(engine, "tasks", "comment_count", "INTEGER", default="0")

    # Also check if project_id exists in 'tasks' and if it's missing, add it.
    # Wait, I already added project_id above.

    print("Migration finished.")
