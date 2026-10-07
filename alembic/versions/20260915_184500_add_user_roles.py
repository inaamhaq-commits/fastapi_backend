from __future__ import annotations

from alembic import op


revision = "20260915_184500"
down_revision = "20260915_181900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT")
    op.execute(
        "UPDATE users SET role = 'user' "
        "WHERE role IS NULL OR role NOT IN ('user', 'manager')"
    )
    op.execute("UPDATE users SET role = 'manager' WHERE lower(email) = 'ali@invozone.com'")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
