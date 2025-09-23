from pydantic import BaseModel, EmailStr

class OrgBase(BaseModel):
    name: str
    email: EmailStr

class OrgCreate(OrgBase):
    password: str

class OrgLogin(BaseModel):
    email: EmailStr
    password: str

class OrgOut(OrgBase):
    id: int
    is_verified: bool

    class Config:
        from_attributes = True
