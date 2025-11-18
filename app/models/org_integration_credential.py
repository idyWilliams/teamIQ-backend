# models/org_integration_credential.py
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from datetime import datetime

class OrgIntegrationCredential(Base):
    __tablename__ = "org_integration_credentials"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, index=True)
    provider = Column(String, index=True)
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

