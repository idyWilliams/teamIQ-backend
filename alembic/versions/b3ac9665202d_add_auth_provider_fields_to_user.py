"""add auth provider fields to user

Revision ID: b3ac9665202d
Revises: 2b49d768632e
Create Date: 2026-05-31 18:07:38.982607

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3ac9665202d'
down_revision: Union[str, Sequence[str], None] = '2b49d768632e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to users table
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True, server_default='local'))
    op.add_column('users', sa.Column('auth_id', sa.String(), nullable=True))
    
    # Update existing users to have 'local' as auth_provider
    op.execute("UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'auth_id')
    op.drop_column('users', 'auth_provider')
