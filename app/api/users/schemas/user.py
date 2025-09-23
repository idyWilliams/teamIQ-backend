from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: str

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    is_organization: bool = False

class UserLogin(UserBase):
    password: str

class UserOut(UserBase):
    id: int
    is_verified: bool
    is_organization: bool

    class Config:
        from_attributes = True
        
    class UserResponse(UserBase):
        id: int

    class Config:
        orm_mode = True

