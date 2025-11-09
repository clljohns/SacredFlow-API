"""add_square_catalog_and_webhooks

Revision ID: 1d2b4f8c3e9a
Revises: f4e2a7d9b8bb
Create Date: 2025-03-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "1d2b4f8c3e9a"
down_revision: Union[str, Sequence[str], None] = "f4e2a7d9b8bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("square_catalog_object_id", sa.String(length=128), nullable=True),
        sa.Column("square_catalog_variation_id", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("square_catalog_object_id", name="uq_products_square_object"),
    )
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)

    op.create_table(
        "square_catalog_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("square_id", sa.String(length=128), nullable=False),
        sa.Column("variation_id", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("square_id", name="uq_square_catalog_items_square_id"),
    )
    op.create_index(op.f("ix_square_catalog_items_square_id"), "square_catalog_items", ["square_id"], unique=False)
    op.create_index(op.f("ix_square_catalog_items_variation_id"), "square_catalog_items", ["variation_id"], unique=False)

    op.create_table(
        "square_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("location_id", sa.String(length=128), nullable=True),
        sa.Column("signature_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_square_webhook_events_event_id"),
    )
    op.create_index(op.f("ix_square_webhook_events_event_type"), "square_webhook_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_square_webhook_events_location_id"), "square_webhook_events", ["location_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_square_webhook_events_location_id"), table_name="square_webhook_events")
    op.drop_index(op.f("ix_square_webhook_events_event_type"), table_name="square_webhook_events")
    op.drop_table("square_webhook_events")

    op.drop_index(op.f("ix_square_catalog_items_variation_id"), table_name="square_catalog_items")
    op.drop_index(op.f("ix_square_catalog_items_square_id"), table_name="square_catalog_items")
    op.drop_table("square_catalog_items")

    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_table("products")

