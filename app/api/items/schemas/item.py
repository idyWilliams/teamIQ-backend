from pydantic import BaseModel

class ItemBase(BaseModel):
    name: str

class ItemCreate(ItemBase):
    owner_id: int

class ItemResponse(ItemBase):
    id: int
    owner_id: int
    class Config:
        orm_mode = True
