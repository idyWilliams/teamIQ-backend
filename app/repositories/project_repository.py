from sqlalchemy.orm import Session
from app.models.project import Item as Project
from app.schemas.project import ItemCreate as ProjectCreate

def create_project(db: Session, project: ProjectCreate):
    new_project = Project(name=project.name, owner_id=project.owner_id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

def list_projects(db: Session):
    return db.query(Project).all()
