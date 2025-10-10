from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from app.core.database import Base
from sqlalchemy.sql import func

class LinkedAccount(Base):
    __tablename__ = "linked_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    provider = Column(String, nullable=False) # e.g., "github", "slack"
    provider_id = Column(String, nullable=False, unique=True) # e.g., github user login
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
