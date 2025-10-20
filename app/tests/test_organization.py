
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# Create a new database for testing
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_organization():
    response = client.post(
        "/api/v1/auth/register/organization",
        json={
            "organization_name": "testorg",
            "team_size": 5,
            "email": "testorg@example.com",
            "password": "testpassword",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Organization created successfully"
    assert data["data"]["organization_name"] == "testorg"
    assert data["data"]["email"] == "testorg@example.com"
