from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.organization import UserRole
import datetime

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    track = Column(String, nullable=True)
    invitation_code = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.utcnow() + datetime.timedelta(hours=48)
    )
    accepted = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    is_used = Column(Boolean, default=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization")
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def status(self):
        if self.accepted and self.is_used:
            return "accepted"
        if self.expires_at < datetime.datetime.now(datetime.timezone.utc):
            return "expired"
        return "pending"
