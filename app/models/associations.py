from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.database import Base

# Many-to-many: Project <-> Stack
project_stack_association = Table(
    'project_stack_association',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('stack_id', Integer, ForeignKey('stacks.id'), primary_key=True)
)

# Many-to-many: Project <-> User (Members)
project_member_association = Table(
    'project_member_association',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)