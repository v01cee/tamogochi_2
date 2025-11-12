"""add notification_intro_seen flag to users

Revision ID: 005_add_notification_intro_seen
Revises: 004_add_morning_touch_sent_at
Create Date: 2025-11-12 00:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_add_notification_intro_seen"
down_revision: Union[str, None] = "004_add_morning_touch_sent_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notification_intro_seen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "notification_intro_seen", schema="public")


