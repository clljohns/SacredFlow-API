"""create payments table

Revision ID: f4e2a7d9b8bb
Revises: c3d8b4e0c0e1
Create Date: 2025-02-15 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4e2a7d9b8bb"
down_revision: Union[str, Sequence[str], None] = "c3d8b4e0c0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("square_payment_id", sa.String(length=128), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=True),
        sa.Column("plan_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_customer_email"), "payments", ["customer_email"], unique=False)
    op.create_index(op.f("ix_payments_square_payment_id"), "payments", ["square_payment_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_square_payment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_customer_email"), table_name="payments")
    op.drop_table("payments")
