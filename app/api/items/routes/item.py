from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.items.models.item import Item
from app.api.items.schemas.item import ItemCreate, ItemResponse

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=ItemResponse)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    new_item = Item(name=item.name, owner_id=item.owner_id)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@router.get("/", response_model=List[ItemResponse])
def list_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
