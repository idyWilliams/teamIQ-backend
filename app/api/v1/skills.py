from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.skill import UserSkillUpdate, SkillRecommendation, UserSkillOut
from app.repositories import skill_repository
from app.schemas.response_model import create_response
from app.core.security import get_current_user_or_organization
from typing import List

router = APIRouter(tags=["skills"])

@router.get("/my-skills", response_model=List[UserSkillOut])
def get_my_skills(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not hasattr(current_user, 'organization_id'):
        raise HTTPException(status_code=403, detail="Users only")
    skills = skill_repository.get_user_skills(db, current_user.id)
    return create_response(success=True, data=[UserSkillOut(skill_name=s.skill.name, level=s.level, updated_at=datetime.utcnow()) for s in skills])

@router.put("/my-skills/{skill_name}")
def update_skill_level(skill_name: str, update: UserSkillUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not hasattr(current_user, 'organization_id'):
        raise HTTPException(status_code=403, detail="Users only")
    skill = skill_repository.get_or_create_skill(db, skill_name)
    us = skill_repository.update_user_skill_level(db, current_user.id, skill.id, update.level)
    return create_response(success=True, message="Skill updated")

@router.get("/recommendations", response_model=List[SkillRecommendation])
def get_recommendations(db: Session = Depends(get_db), current_user=Depends(get_current_user_or_organization)):
    if not hasattr(current_user, 'organization_id'):
        raise HTTPException(status_code=403, detail="Users only")
    recs = skill_repository.get_skill_recommendations(db, current_user.id)
    return create_response(success=True, data=recs)