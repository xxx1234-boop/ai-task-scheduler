"""add status column to schedules

Revision ID: c000a2c4a88e
Revises: ba17f3defae0
Create Date: 2026-01-07 16:28:32.728386

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'c000a2c4a88e'
down_revision = 'ba17f3defae0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column to schedules table
    op.add_column(
        'schedules',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='scheduled')
    )

    # Add check constraint for status values
    op.create_check_constraint(
        'schedules_status_check',
        'schedules',
        "status IN ('scheduled', 'completed', 'skipped')"
    )


def downgrade() -> None:
    # Drop check constraint first
    op.drop_constraint('schedules_status_check', 'schedules', type_='check')
    # Drop status column
    op.drop_column('schedules', 'status')
