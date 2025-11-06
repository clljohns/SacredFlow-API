"""fix async schema

Revision ID: 28a986ccfe85
Revises: 21cb1455cf2e
Create Date: 2025-11-06 09:19:20.809390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28a986ccfe85'
down_revision: Union[str, Sequence[str], None] = '21cb1455cf2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
