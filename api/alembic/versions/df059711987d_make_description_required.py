"""Make description required

Revision ID: df059711987d
Revises: a08e42e1b033
Create Date: 2026-01-08 16:10:41.079584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'df059711987d'
down_revision = 'a08e42e1b033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, update NULL values to empty string
    op.execute("UPDATE tasks SET description = '' WHERE description IS NULL")
    # Then, add NOT NULL constraint
    op.alter_column('tasks', 'description',
               existing_type=sa.TEXT(),
               nullable=False)


def downgrade() -> None:
    op.alter_column('tasks', 'description',
               existing_type=sa.TEXT(),
               nullable=True)
