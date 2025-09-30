import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env file into environment variables
load_dotenv()

# Prefer internal DB if available (Render), else fall back to external
DATABASE_URL = os.getenv("INTERNAL_DATABASE_URL") or os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL or INTERNAL_DATABASE_URL found in environment variables")

# Add SSL configuration and connection improvements
engine = create_engine(
    DATABASE_URL,
    echo=True,
    future=True,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 60
    },
    pool_pre_ping=True,      # Test connections before use
    pool_recycle=3600,       # Recycle connections every hour
    pool_timeout=30,         # Timeout for getting connection from pool
    max_overflow=10          # Allow extra connections beyond pool size
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
