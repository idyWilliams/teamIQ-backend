from sqlalchemy import Column, Integer, ForeignKey
from app.core.database import Base

class UserStack(Base):
    __tablename__ = "user_stacks"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    stack_id = Column(Integer, ForeignKey("stacks.id"), primary_key=True)


