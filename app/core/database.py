import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
    connect_args={
        "sslmode": "prefer",
        "connect_timeout": 60
    },
    use_native_hstore=False,
    pool_pre_ping=True,
   pool_recycle=300, 
    pool_timeout=30,
    max_overflow=10
)

# Debug logging for DB connection
try:
    from urllib.parse import urlparse
    result = urlparse(DATABASE_URL)
    print(f"DEBUG: Connecting to database at {result.hostname} (SSL: prefer)")
except Exception as e:
    print(f"DEBUG: Could not parse DATABASE_URL for logging: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()