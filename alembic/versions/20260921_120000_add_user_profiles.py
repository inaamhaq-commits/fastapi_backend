from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260921_120000"
down_revision = "20260915_184500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.Uuid(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])
    op.add_column("clients", sa.Column("profile_id", sa.Uuid(as_uuid=False), nullable=True))
    op.create_index("ix_clients_profile_id", "clients", ["profile_id"])
    op.create_foreign_key(
        "fk_clients_profile_id_user_profiles",
        "clients",
        "user_profiles",
        ["profile_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_clients_profile_id_user_profiles", "clients", type_="foreignkey")
    op.drop_index("ix_clients_profile_id", table_name="clients")
    op.drop_column("clients", "profile_id")
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
