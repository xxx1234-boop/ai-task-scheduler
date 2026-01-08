"""Add description field to tasks

Revision ID: a08e42e1b033
Revises: b2c3d4e5f6g7
Create Date: 2026-01-08 16:04:45.314943

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a08e42e1b033'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'description')
