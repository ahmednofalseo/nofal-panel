"""add plugins table

Revision ID: 1b9f1c2a4e01
Revises: 6c5d0b6a9d0a
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "1b9f1c2a4e01"
down_revision = "6c5d0b6a9d0a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("plugins"):
        return
    op.create_table(
        "plugins",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=True, server_default="0.0.0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_plugins_id", "plugins", ["id"])
    op.create_index("ix_plugins_name", "plugins", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_plugins_name", table_name="plugins")
    op.drop_index("ix_plugins_id", table_name="plugins")
    op.drop_table("plugins")

