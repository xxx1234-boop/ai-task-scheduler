"""fix foreign key cascade constraints

Revision ID: a1b2c3d4e5f6
Revises: 699d11d39f42
Create Date: 2026-01-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '699d11d39f42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix all foreign key constraints with proper ON DELETE behavior.

    CASCADE behavior (delete child when parent is deleted):
    - schedules.task_id -> tasks.id
    - time_entries.task_id -> tasks.id
    - task_dependencies.task_id -> tasks.id
    - task_dependencies.depends_on_task_id -> tasks.id
    - tasks.parent_task_id -> tasks.id

    SET NULL behavior (optional FK, set to NULL when parent deleted):
    - tasks.project_id -> projects.id
    - tasks.genre_id -> genres.id
    """

    # 1. Fix task_dependencies foreign keys (need CASCADE)
    op.drop_constraint(
        'task_dependencies_task_id_fkey',
        'task_dependencies',
        type_='foreignkey'
    )
    op.drop_constraint(
        'task_dependencies_depends_on_task_id_fkey',
        'task_dependencies',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'task_dependencies_task_id_fkey',
        'task_dependencies',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'task_dependencies_depends_on_task_id_fkey',
        'task_dependencies',
        'tasks',
        ['depends_on_task_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Recreate index that was dropped in previous migration
    op.create_index(
        'idx_task_deps_depends_on',
        'task_dependencies',
        ['depends_on_task_id']
    )

    # 2. Fix tasks.parent_task_id (change to CASCADE)
    op.drop_constraint(
        'tasks_parent_task_id_fkey',
        'tasks',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'tasks_parent_task_id_fkey',
        'tasks',
        'tasks',
        ['parent_task_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # 3. Fix tasks.project_id (add SET NULL)
    op.drop_constraint(
        'tasks_project_id_fkey',
        'tasks',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'tasks_project_id_fkey',
        'tasks',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 4. Fix tasks.genre_id (add SET NULL)
    op.drop_constraint(
        'tasks_genre_id_fkey',
        'tasks',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'tasks_genre_id_fkey',
        'tasks',
        'genres',
        ['genre_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # 5. Fix schedules.task_id (add CASCADE)
    op.drop_constraint(
        'schedules_task_id_fkey',
        'schedules',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'schedules_task_id_fkey',
        'schedules',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # 6. Fix time_entries.task_id (add CASCADE)
    op.drop_constraint(
        'time_entries_task_id_fkey',
        'time_entries',
        type_='foreignkey'
    )
    op.create_foreign_key(
        'time_entries_task_id_fkey',
        'time_entries',
        'tasks',
        ['task_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """
    Revert to foreign keys without ON DELETE behavior.
    Note: This is destructive - data may have been cascade-deleted.
    """

    # 1. Revert time_entries.task_id
    op.drop_constraint('time_entries_task_id_fkey', 'time_entries', type_='foreignkey')
    op.create_foreign_key(
        'time_entries_task_id_fkey',
        'time_entries',
        'tasks',
        ['task_id'],
        ['id']
    )

    # 2. Revert schedules.task_id
    op.drop_constraint('schedules_task_id_fkey', 'schedules', type_='foreignkey')
    op.create_foreign_key(
        'schedules_task_id_fkey',
        'schedules',
        'tasks',
        ['task_id'],
        ['id']
    )

    # 3. Revert tasks.genre_id
    op.drop_constraint('tasks_genre_id_fkey', 'tasks', type_='foreignkey')
    op.create_foreign_key(
        'tasks_genre_id_fkey',
        'tasks',
        'genres',
        ['genre_id'],
        ['id']
    )

    # 4. Revert tasks.project_id
    op.drop_constraint('tasks_project_id_fkey', 'tasks', type_='foreignkey')
    op.create_foreign_key(
        'tasks_project_id_fkey',
        'tasks',
        'projects',
        ['project_id'],
        ['id']
    )

    # 5. Revert tasks.parent_task_id
    op.drop_constraint('tasks_parent_task_id_fkey', 'tasks', type_='foreignkey')
    op.create_foreign_key(
        'tasks_parent_task_id_fkey',
        'tasks',
        'tasks',
        ['parent_task_id'],
        ['id']
    )

    # 6. Revert task_dependencies
    op.drop_index('idx_task_deps_depends_on', table_name='task_dependencies')
    op.drop_constraint('task_dependencies_depends_on_task_id_fkey', 'task_dependencies', type_='foreignkey')
    op.drop_constraint('task_dependencies_task_id_fkey', 'task_dependencies', type_='foreignkey')
    op.create_foreign_key(
        'task_dependencies_task_id_fkey',
        'task_dependencies',
        'tasks',
        ['task_id'],
        ['id']
    )
    op.create_foreign_key(
        'task_dependencies_depends_on_task_id_fkey',
        'task_dependencies',
        'tasks',
        ['depends_on_task_id'],
        ['id']
    )
