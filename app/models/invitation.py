
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.organization import UserRole
from sqlalchemy.types import Enum as SQLEnum
import datetime

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    stack = Column(String, nullable=True)
    invitation_code = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow() + datetime.timedelta(days=1))
    accepted = Column(Boolean, default=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))

    organization = relationship("Organization")
