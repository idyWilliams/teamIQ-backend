# test_supabase_correct.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# From your screenshot: project reference is "jdntkpywtpabkytmouei"
PROJECT_REF = "jdntkpywtpabkytmouei"
PASSWORD = "Williams123+"

# Correct Transaction pooler format - include project reference in username
DATABASE_URL = f"postgresql://postgres.{PROJECT_REF}:{PASSWORD}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

print("Testing Supabase Transaction Pooler with project reference...")
print(f"URL: {DATABASE_URL[:60]}...")

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print("✅ Connection successful!")
        print(f"PostgreSQL version: {version}")

except Exception as e:
    print(f"❌ Connection failed: {e}")

    # Try direct connection as backup
    print("\nTrying direct connection...")
    direct_url = f"postgresql://postgres:{PASSWORD}@db.{PROJECT_REF}.supabase.co:5432/postgres"

    try:
        engine2 = create_engine(direct_url)
        with engine2.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Direct connection successful!")
            print(f"Use this URL: {direct_url}")
    except Exception as e2:
        print(f"❌ Direct connection also failed: {e2}")
