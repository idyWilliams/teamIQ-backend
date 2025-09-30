from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base

class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    provider = Column(String, nullable=False) # e.g., "github", "slack"
    provider_id = Column(String, nullable=False, unique=True) # e.g., github user login
