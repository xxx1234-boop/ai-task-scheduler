"""add updated_at triggers for all tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08 12:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


# Tables that have updated_at column
TABLES_WITH_UPDATED_AT = [
    'genres',
    'projects',
    'tasks',
    'schedules',
    'time_entries',
    'settings',
]


def upgrade() -> None:
    """
    Create a reusable trigger function for auto-updating updated_at column,
    then apply it to all tables with updated_at.
    """

    # 1. Create the trigger function
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 2. Create triggers for each table
    for table in TABLES_WITH_UPDATED_AT:
        trigger_name = f"trigger_{table}_updated_at"
        op.execute(f"""
        CREATE TRIGGER {trigger_name}
            BEFORE UPDATE
            ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """
    Remove all updated_at triggers and the shared function.
    """

    # 1. Drop triggers from each table (in reverse order)
    for table in reversed(TABLES_WITH_UPDATED_AT):
        trigger_name = f"trigger_{table}_updated_at"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table};")

    # 2. Drop the shared function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
