from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum 
from app.db.database import Base

#Class for roles for signing up eg intern and mentor and organization
class UserRole(PyEnum):
    INTERN = "intern"
    MENTOR = "mentor"
    ORGANIZATION = "organization"
# a class-based models with the user models that will be crucial for login and signup purposes
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable= False)
    last_name = Column(String, nullable = False)
    username = Column(String, unique=True, index=True, nullable=False)
    country = Column(String, nullable = False)
    hashed_password = Column(String, nullable = False)
    role = Column(Enum(UserRole), default = UserRole.INTERN, nullable = False)
    
    
# class-based model for those signing up as an organization

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key = True, index = True)
    organization_name = Column(String, unique = True, index = False, nullable = False)
    team_size = Column(Integer, nullable = False)
    hashed_password = Column(String, nullable = False)
    role = Column(Enum(UserRole), default = UserRole.ORGANIZATION, nullable = False)
    
    
    
    
    