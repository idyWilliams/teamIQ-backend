"""add auth provider fields to organization

Revision ID: fb98003ce35a
Revises: b3ac9665202d
Create Date: 2026-05-31 18:28:37.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb98003ce35a'
down_revision: Union[str, Sequence[str], None] = 'b3ac9665202d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('auth_provider', sa.String(), nullable=True, server_default='local'))
    op.add_column('organizations', sa.Column('auth_id', sa.String(), nullable=True))
    op.execute("UPDATE organizations SET auth_provider = 'local' WHERE auth_provider IS NULL")


def downgrade() -> None:
    op.drop_column('organizations', 'auth_id')
    op.drop_column('organizations', 'auth_provider')
