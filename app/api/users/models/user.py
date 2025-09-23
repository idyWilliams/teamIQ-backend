from sqlalchemy import Column, Integer, String, Boolean
from app.db.database import Base

# a class-based models with the user models that will be crucial for login and signup purposes
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable = False)
    is_organization = Column(Boolean, defualt = False)
    
    
    