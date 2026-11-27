"""Add user auth columns and oauth_account table."""

import sqlalchemy as sa
from alembic import op

revision = "b8e2f1a9c3d4"
down_revision = "415b7468c104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_user", sa.Column("avatar_url", sa.String(length=1000), nullable=True))
    op.add_column("app_user", sa.Column("password_hash", sa.String(length=255), nullable=True))

    op.create_table(
        "oauth_account",
        sa.Column("oauth_account_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("provider_username", sa.String(length=255), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("scopes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("provider IN ('github', 'google')", name="ck_oauth_provider"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("oauth_account_id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        sa.UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),
    )
    op.create_index("idx_oauth_account_user_id", "oauth_account", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_oauth_account_user_id", table_name="oauth_account")
    op.drop_table("oauth_account")
    op.drop_column("app_user", "password_hash")
    op.drop_column("app_user", "avatar_url")
