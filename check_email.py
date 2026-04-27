#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    # Check for user with case-insensitive email search
    print("=== Searching for wangoinjoroge450@gmail.com (case-insensitive) ===")
    result = db.execute(text("""
        SELECT id, email, first_name, last_name
        FROM users
        WHERE LOWER(email) = LOWER('Wangoinjoroge450@gmail.com')
    """))
    user = result.fetchone()
    if user:
        print(f"Found user: ID {user[0]}, Email: {user[1]}, Name: {user[2]} {user[3]}")

        # Check if linked to org 97
        link_result = db.execute(text("""
            SELECT id FROM user_organizations
            WHERE user_id = :user_id AND organization_id = 97
        """), {"user_id": user[0]})
        link = link_result.fetchone()
        if link:
            print(f"✅ User IS linked to org 97 (link ID: {link[0]})")
        else:
            print(f"❌ User NOT linked to org 97 - THIS IS THE BUG!")
            print(f"Need to create link for user_id={user[0]}, org_id=97")
    else:
        print("User not found even with case-insensitive search")

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
