from  sqlalchemy import Column, Integer, Boolean, String
from app.db.database import Base

#the class-based for organization that will be used for organizations using the Team-IQ app with its fields

class Organization(Base):
    __tablename__ = "Organizations"
    id = Column(Integer, primary_key = True, index =True)
    name = Column(String, unique = True, nullable =False)
    organization_email = Column(String, unique = True, index = True, nullable = False)
    hashed_password = Column(String, nullable = False)