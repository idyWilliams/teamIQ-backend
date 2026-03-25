import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    pool_pre_ping=True,
)

# Debug: test once
try:
    from urllib.parse import urlparse
    result = urlparse(DATABASE_URL)
    print(f"DEBUG: Connecting to {result.hostname}:{result.port}")
    with engine.connect() as conn:
        print("DEBUG: DB VERSION TEST:", conn.execute(text("select version()")).scalar())
except Exception as e:
    print("DEBUG: Failed initial DB test:", e)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
