from sqlalchemy import Column, Integer, String
from sqlalchemy.types import Enum as SQLEnum
from app.core.database import Base
from enum import Enum as PyEnum

class UserRole(PyEnum):
    INTERN = "intern"
    MENTOR = "mentor"
    ORGANIZATION = "organization"

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    organization_name = Column(String, unique=True, nullable=False)
    team_size = Column(Integer, nullable=False)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )