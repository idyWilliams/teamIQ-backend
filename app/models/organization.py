from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.types import Enum as SQLEnum
from app.core.database import Base
from enum import Enum as PyEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

class UserRole(PyEnum):
    INTERN = "intern"
    MENTOR = "mentor"
    ORGANIZATION = "organization"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    organization_name = Column(String, unique=True, nullable=False)
    team_size = Column(String, nullable=False) 
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    organization_image = Column(String, nullable=True)
    description = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    social_media_handles = Column(JSON, nullable=True)
    domain_link = Column(String, nullable=True)
    favorite_tools = Column(JSON, nullable=True)
    website = Column(String, nullable=True)
    country = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    users = relationship("User", back_populates="organization")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())  # Fixed: Added server_default for INSERT