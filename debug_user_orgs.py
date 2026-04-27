#!/usr/bin/env python3
"""
Debug script to check user_organizations table
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.organization import Organization
from app.models.user_organizations import UserOrganization

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Connecting to database...")

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Check if user_organizations table exists
    print("\n=== Checking if user_organizations table exists ===")
    result = db.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'user_organizations'
        );
    """))
    table_exists = result.scalar()
    print(f"Table exists: {table_exists}")

    if table_exists:
        # Count rows
        print("\n=== Counting rows in user_organizations ===")
        result = db.execute(text("SELECT COUNT(*) FROM user_organizations"))
        count = result.scalar()
        print(f"Total rows: {count}")

        # Show all rows
        if count > 0:
            print("\n=== All user_organizations entries ===")
            result = db.execute(text("SELECT * FROM user_organizations"))
            for row in result:
                print(f"ID: {row[0]}, User ID: {row[1]}, Org ID: {row[2]}")

        # Check organization 97
        print("\n=== Users in organization 97 ===")
        result = db.execute(text("""
            SELECT u.id, u.email, u.first_name, u.last_name
            FROM users u
            JOIN user_organizations uo ON u.id = uo.user_id
            WHERE uo.organization_id = 97
        """))
        users = result.fetchall()
        if users:
            for user in users:
                print(f"User ID: {user[0]}, Email: {user[1]}, Name: {user[2]} {user[3]}")
        else:
            print("No users found for organization 97")

        # Check invitations for org 97
        print("\n=== Accepted invitations for organization 97 ===")
        result = db.execute(text("""
            SELECT id, email, status, accepted, is_used, accepted_at
            FROM invitations
            WHERE organization_id = 97 AND status = 'accepted'
        """))
        invitations = result.fetchall()
        if invitations:
            for inv in invitations:
                print(f"Invitation ID: {inv[0]}, Email: {inv[1]}, Status: {inv[2]}, Accepted: {inv[3]}, Used: {inv[4]}, Accepted At: {inv[5]}")

                # Check if user exists with this email
                user_result = db.execute(text("SELECT id, email FROM users WHERE email = :email"), {"email": inv[1]})
                user = user_result.fetchone()
                if user:
                    print(f"  -> User exists: ID {user[0]}, Email: {user[1]}")

                    # Check if linked
                    link_result = db.execute(text("""
                        SELECT id FROM user_organizations
                        WHERE user_id = :user_id AND organization_id = 97
                    """), {"user_id": user[0]})
                    link = link_result.fetchone()
                    if link:
                        print(f"  -> ✅ Linked to org 97 (link ID: {link[0]})")
                    else:
                        print(f"  -> ❌ NOT linked to org 97!")
                else:
                    print(f"  -> ❌ User does not exist!")
        else:
            print("No accepted invitations found")
    else:
        print("❌ user_organizations table does not exist!")
        print("You need to run database migrations to create this table.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
