from sqlalchemy.orm import Session
from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate

def create_project(db: Session, project: ProjectCreate, org_id: int = None):
    new_project = Project(name=project.name, owner_id=project.owner_id, organization_id=org_id)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

def list_projects(db: Session, user_id: int = None, org_id: int = None, status: ProjectStatus = ProjectStatus.ACTIVE):

    query = db.query(Project).filter(Project.status == status)

    if user_id:

        query = query.filter(Project.owner_id == user_id)

    if org_id:

        query = query.filter(Project.organization_id == org_id)

    return query.all()



def get_users_for_project(db: Session, project_id: int):

    """Get all users who are members of a specific project."""

    from app.models.user import User

    return db.query(User).join(User.projects).filter(Project.id == project_id).all()
