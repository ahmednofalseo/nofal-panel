"""add port registry

Revision ID: 6c5d0b6a9d0a
Revises: f34438d06712
Create Date: 2026-04-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6c5d0b6a9d0a"
down_revision = "f34438d06712"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "port_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("purpose", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_port_registry_id", "port_registry", ["id"], unique=False)
    op.create_index("ix_port_registry_port", "port_registry", ["port"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_port_registry_port", table_name="port_registry")
    op.drop_index("ix_port_registry_id", table_name="port_registry")
    op.drop_table("port_registry")

