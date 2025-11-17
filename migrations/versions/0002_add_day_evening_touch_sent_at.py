"""add_day_evening_touch_sent_at

Revision ID: 0002
Revises: 0001_initial
Create Date: 2025-11-15 03:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поля day_touch_sent_at и evening_touch_sent_at в таблицу users
    op.add_column("users", sa.Column("day_touch_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("evening_touch_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Удаляем поля day_touch_sent_at и evening_touch_sent_at из таблицы users
    op.drop_column("users", "evening_touch_sent_at")
    op.drop_column("users", "day_touch_sent_at")

