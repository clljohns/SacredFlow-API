"""create square checkout links

Revision ID: c3d8b4e0c0e1
Revises: 8b2fef4d2d1b
Create Date: 2025-02-15 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3d8b4e0c0e1"
down_revision: Union[str, Sequence[str], None] = "8b2fef4d2d1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "square_checkout_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.String(length=64), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("plan_type", sa.String(length=64), nullable=False, server_default="subscription"),
        sa.Column("cta_label", sa.String(length=128), nullable=True),
        sa.Column("features", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_square_checkout_links_slug"), "square_checkout_links", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_square_checkout_links_slug"), table_name="square_checkout_links")
    op.drop_table("square_checkout_links")
