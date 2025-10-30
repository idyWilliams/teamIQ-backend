from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.organization import UserRole
from sqlalchemy.sql import func


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
        Enum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.INTERN,
        nullable=False
    )
    profile_image = Column(String, nullable=True)  # New field
    bio = Column(String, nullable=True)  # New field
    phone_number = Column(String, nullable=True)  # New field
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    # organization = relationship("Organization", back_populates="users")
    tasks = relationship("Task", back_populates="owner")
    owned_projects = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="[Project.owner_id]",  # explicitly use Project.owner_id
    )
    user_skills = relationship("UserSkill", back_populates="user")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    organizations = relationship("Organization",
                                 secondary="user_organizations",
                                 back_populates="users")
