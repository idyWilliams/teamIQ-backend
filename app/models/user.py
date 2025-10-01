from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.organization import UserRole

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    country = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.INTERN,
        nullable=False
    )
    tasks = relationship("Task", back_populates="owner")
    projects = relationship("Project", back_populates="owner")