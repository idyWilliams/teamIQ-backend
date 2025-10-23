from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from app.core.database import Base


class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    # Prevent duplicate link between the same user/org pair
    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="_user_org_uc"),)
