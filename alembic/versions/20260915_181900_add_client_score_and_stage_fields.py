from __future__ import annotations

from alembic import op


revision = "20260915_181900"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS score INTEGER")
    op.execute("UPDATE clients SET score = 0 WHERE score IS NULL")
    op.execute("ALTER TABLE clients ALTER COLUMN score SET DEFAULT 0")
    op.execute("ALTER TABLE clients ALTER COLUMN score SET NOT NULL")

    for column_name in (
        "calls_scheduled",
        "qualified",
        "pre_sale",
        "not_a_fit",
    ):
        op.execute(f"ALTER TABLE clients ADD COLUMN IF NOT EXISTS {column_name} BOOLEAN")
        op.execute(f"UPDATE clients SET {column_name} = false WHERE {column_name} IS NULL")
        op.execute(f"ALTER TABLE clients ALTER COLUMN {column_name} SET DEFAULT false")
        op.execute(f"ALTER TABLE clients ALTER COLUMN {column_name} SET NOT NULL")


def downgrade() -> None:
    for column_name in (
        "not_a_fit",
        "pre_sale",
        "qualified",
        "calls_scheduled",
    ):
        op.execute(f"ALTER TABLE clients DROP COLUMN IF EXISTS {column_name}")
