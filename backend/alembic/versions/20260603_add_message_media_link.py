"""add message media link fields

Revision ID: 20260603msgmedia
Revises: 20260603addobs
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260603msgmedia"
down_revision: Union[str, Sequence[str], None] = "20260603addobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("message", sa.Column("media_url", sa.VARCHAR(), nullable=True))
    op.add_column("message", sa.Column("media_type", sa.VARCHAR(), nullable=True))


def downgrade() -> None:
    op.drop_column("message", "media_type")
    op.drop_column("message", "media_url")
