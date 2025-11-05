from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.database import Base

# Many-to-many: User <-> Organization
user_organizations = Table(
    'user_organizations',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True)
)

# Many-to-many: User <-> Stack
user_stacks = Table(
    'user_stacks',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('stack_id', Integer, ForeignKey('stacks.id'), primary_key=True)
)
