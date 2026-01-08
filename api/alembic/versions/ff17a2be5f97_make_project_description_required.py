"""Make project description required

Revision ID: ff17a2be5f97
Revises: df059711987d
Create Date: 2026-01-08 16:21:32.642935

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff17a2be5f97'
down_revision = 'df059711987d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, update NULL values to empty string
    op.execute("UPDATE projects SET description = '' WHERE description IS NULL")
    # Then, add NOT NULL constraint
    op.alter_column('projects', 'description',
               existing_type=sa.VARCHAR(),
               nullable=False)


def downgrade() -> None:
    op.alter_column('projects', 'description',
               existing_type=sa.VARCHAR(),
               nullable=True)
