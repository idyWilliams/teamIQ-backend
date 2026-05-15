from sqlalchemy import Boolean, Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.organization import UserRole
from sqlalchemy.sql import func
import datetime


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
    profile_image = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    track = Column(String, nullable=True)


    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tasks = relationship("Task", back_populates="owner")

    owned_projects = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="[Project.owner_id]",
    )

    led_projects = relationship(
        "Project",
        back_populates="project_lead",
        foreign_keys="[Project.project_lead_id]",
    )

    user_skills = relationship("UserSkill", back_populates="user")

    organizations = relationship(
        "Organization",
        secondary="user_organizations",
        back_populates="users"
    )

    stacks = relationship("Stack", secondary="user_stacks", back_populates="users")
    dashboard = relationship("UserDashboard", back_populates="user", uselist=False)
    onboarding_completed = Column(Boolean, default=False)
    onboarding_step = Column(Integer, default=0) 
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def job_title(self):
        return self.track or self.role.value

    @property
    def avatar_url(self):
        return self.profile_image

    @property
    def online_status(self):
        if self.last_seen:
            now = datetime.datetime.now(datetime.timezone.utc)
            ls = self.last_seen
            if ls.tzinfo is None:
                ls = ls.replace(tzinfo=datetime.timezone.utc)
            if (now - ls) < datetime.timedelta(minutes=5):
                return "online"
        return "offline"

    @property
    def skills(self):
        return self.user_skills