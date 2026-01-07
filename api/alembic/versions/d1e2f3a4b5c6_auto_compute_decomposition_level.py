"""auto compute decomposition_level via database triggers

Revision ID: d1e2f3a4b5c6
Revises: c000a2c4a88e
Create Date: 2026-01-08 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c000a2c4a88e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create database triggers to automatically compute decomposition_level
    based on parent_task_id hierarchy.
    """

    # 1. Create trigger function for INSERT/UPDATE
    op.execute("""
    CREATE OR REPLACE FUNCTION update_decomposition_level_on_change()
    RETURNS TRIGGER AS $$
    BEGIN
        -- If no parent, level is 0 (root task)
        IF NEW.parent_task_id IS NULL THEN
            NEW.decomposition_level := 0;
        ELSE
            -- Get parent's decomposition_level and add 1
            SELECT COALESCE(decomposition_level, 0) + 1
            INTO NEW.decomposition_level
            FROM tasks
            WHERE id = NEW.parent_task_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 2. Create trigger on tasks table
    op.execute("""
    CREATE TRIGGER trigger_auto_decomposition_level
        BEFORE INSERT OR UPDATE OF parent_task_id
        ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION update_decomposition_level_on_change();
    """)

    # 3. Create cascading trigger function (updates all descendants when parent changes)
    op.execute("""
    CREATE OR REPLACE FUNCTION cascade_decomposition_level()
    RETURNS TRIGGER AS $$
    BEGIN
        -- Only proceed if parent_task_id actually changed
        IF (TG_OP = 'UPDATE' AND OLD.parent_task_id IS DISTINCT FROM NEW.parent_task_id) THEN
            -- Recursively update all descendants
            WITH RECURSIVE descendants AS (
                -- Direct children
                SELECT id FROM tasks WHERE parent_task_id = NEW.id
                UNION ALL
                -- Descendants of descendants
                SELECT t.id FROM tasks t
                INNER JOIN descendants d ON t.parent_task_id = d.id
            )
            -- Trigger the BEFORE UPDATE trigger for each descendant by updating parent_task_id to itself
            UPDATE tasks
            SET parent_task_id = parent_task_id
            WHERE id IN (SELECT id FROM descendants);
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 4. Create cascading trigger
    op.execute("""
    CREATE TRIGGER trigger_cascade_decomposition
        AFTER UPDATE OF parent_task_id
        ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION cascade_decomposition_level();
    """)

    # 5. Backfill existing data (recalculate all decomposition_levels)
    op.execute("""
    WITH RECURSIVE task_hierarchy AS (
        -- Base case: root tasks (no parent)
        SELECT id, parent_task_id, 0 as level
        FROM tasks
        WHERE parent_task_id IS NULL

        UNION ALL

        -- Recursive case: children of tasks in hierarchy
        SELECT t.id, t.parent_task_id, th.level + 1
        FROM tasks t
        INNER JOIN task_hierarchy th ON t.parent_task_id = th.id
    )
    UPDATE tasks t
    SET decomposition_level = th.level
    FROM task_hierarchy th
    WHERE t.id = th.id;
    """)


def downgrade() -> None:
    """
    Remove database triggers and functions.

    Note: decomposition_level column remains, but reverts to manual management.
    """
    # Remove triggers (in reverse order)
    op.execute("DROP TRIGGER IF EXISTS trigger_cascade_decomposition ON tasks;")
    op.execute("DROP TRIGGER IF EXISTS trigger_auto_decomposition_level ON tasks;")

    # Remove functions
    op.execute("DROP FUNCTION IF EXISTS cascade_decomposition_level();")
    op.execute("DROP FUNCTION IF EXISTS update_decomposition_level_on_change();")
