from pydantic import BaseModel
import datetime

class SkillCreate(BaseModel):
    name: str

class UserSkillUpdate(BaseModel):
    level: float

class UserSkillOut(BaseModel):
    skill_name: str
    level: float
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class SkillRecommendation(BaseModel):
    skill: str
    urgency: str  # high/medium/low