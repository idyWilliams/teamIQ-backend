"""Add project type industry and methodology

Revision ID: 2b49d768632e
Revises: 1b49d768632e
Create Date: 2026-05-29 13:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2b49d768632e'
down_revision: Union[str, Sequence[str], None] = '1b49d768632e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ProjectType enum
    op.execute("CREATE TYPE projecttype AS ENUM ('software_development', 'business_management', 'strategy_consulting', 'marketing_creative', 'research_development', 'other')")
    
    # Add columns to projects table
    op.add_column('projects', sa.Column('project_type', sa.Enum('software_development', 'business_management', 'strategy_consulting', 'marketing_creative', 'research_development', 'other', name='projecttype'), nullable=True))
    op.add_column('projects', sa.Column('industry', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('methodology', sa.String(), nullable=True))
    
    # Set default value for existing projects
    op.execute("UPDATE projects SET project_type = 'software_development' WHERE project_type IS NULL")


def downgrade() -> None:
    # Remove columns
    op.drop_column('projects', 'project_type')
    op.drop_column('projects', 'industry')
    op.drop_column('projects', 'methodology')
    
    # Drop enum type
    op.execute("DROP TYPE projecttype")
