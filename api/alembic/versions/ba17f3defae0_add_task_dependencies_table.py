"""add task_dependencies table

Revision ID: ba17f3defae0
Revises: ce5485372f5b
Create Date: 2026-01-07 16:28:05.799859

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'ba17f3defae0'
down_revision = 'ce5485372f5b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create task_dependencies table
    op.create_table(
        'task_dependencies',
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('depends_on_task_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['depends_on_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'depends_on_task_id'),
        sa.CheckConstraint('task_id != depends_on_task_id', name='no_self_reference')
    )

    # Create index for efficient lookup of blocking tasks
    op.create_index(
        'idx_task_deps_depends_on',
        'task_dependencies',
        ['depends_on_task_id']
    )


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_task_deps_depends_on', table_name='task_dependencies')
    # Drop table
    op.drop_table('task_dependencies')
