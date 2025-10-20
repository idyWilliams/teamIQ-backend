from sqlalchemy.orm import Session
from app.models.skill import Skill, UserSkill
from app.schemas.skill import SkillCreate, UserSkillUpdate

def get_or_create_skill(db: Session, name: str) -> Skill:
    skill = db.query(Skill).filter(Skill.name == name).first()
    if not skill:
        skill = Skill(name=name)
        db.add(skill)
        db.commit()
        db.refresh(skill)
    return skill

def get_user_skills(db: Session, user_id: int):
    return db.query(UserSkill).filter(UserSkill.user_id == user_id).all()

def update_user_skill_level(db: Session, user_id: int, skill_id: int, level: float):
    us = db.query(UserSkill).filter(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id).first()
    if not us:
        us = UserSkill(user_id=user_id, skill_id=skill_id, level=level)
        db.add(us)
    else:
        us.level = level
    db.commit()
    db.refresh(us)
    return us

def get_skill_recommendations(db: Session, user_id: int):  # Dummy for MVP
    skills = get_user_skills(db, user_id)
    low_skills = [s for s in skills if s.level < 50]
    return [{"skill": s.skill.name, "urgency": "high"} for s in low_skills[:3]] if low_skills else [{"skill": "Python", "urgency": "medium"}]