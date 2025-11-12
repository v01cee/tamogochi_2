"""add notification times to users

Revision ID: 008_add_notification_times
Revises: 007_create_touch_contents_table
Create Date: 2025-11-12 01:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "008_add_notification_times"
down_revision: Union[str, None] = "007_create_touch_contents_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("morning_notification_time", sa.Time(timezone=False), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("day_notification_time", sa.Time(timezone=False), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("evening_notification_time", sa.Time(timezone=False), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "evening_notification_time", schema="public")
    op.drop_column("users", "day_notification_time", schema="public")
    op.drop_column("users", "morning_notification_time", schema="public")


