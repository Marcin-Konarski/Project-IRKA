"""add message telegram_url field

Revision ID: 20260603msgtgurl
Revises: 20260603msgmedia
Create Date: 2026-06-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260603msgtgurl"
down_revision: Union[str, Sequence[str], None] = "20260603msgmedia"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("message", sa.Column("telegram_url", sa.VARCHAR(), nullable=True))


def downgrade() -> None:
    op.drop_column("message", "telegram_url")
