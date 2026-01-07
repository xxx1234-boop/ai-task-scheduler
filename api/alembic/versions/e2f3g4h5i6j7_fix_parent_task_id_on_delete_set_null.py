"""fix parent_task_id foreign key to ON DELETE SET NULL

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3a4b5c6
Create Date: 2026-01-08 01:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3g4h5i6j7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix parent_task_id foreign key constraint to include ON DELETE SET NULL.
    This ensures that when a parent task is deleted, child tasks become orphaned
    (parent_task_id set to NULL) rather than causing a foreign key violation.
    """

    # Drop existing foreign key constraint
    op.drop_constraint(
        'tasks_parent_task_id_fkey',
        'tasks',
        type_='foreignkey'
    )

    # Recreate with ON DELETE SET NULL
    op.create_foreign_key(
        'tasks_parent_task_id_fkey',
        'tasks',
        'tasks',
        ['parent_task_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Revert to original foreign key constraint without ON DELETE SET NULL.
    """

    # Drop the modified constraint
    op.drop_constraint(
        'tasks_parent_task_id_fkey',
        'tasks',
        type_='foreignkey'
    )

    # Recreate without ON DELETE SET NULL
    op.create_foreign_key(
        'tasks_parent_task_id_fkey',
        'tasks',
        'tasks',
        ['parent_task_id'],
        ['id']
    )
