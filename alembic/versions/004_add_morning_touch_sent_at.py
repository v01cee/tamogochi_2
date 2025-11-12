"""add morning_touch_sent_at to users

Revision ID: 004_add_morning_touch_sent_at
Revises: 003_add_user_management_fields
Create Date: 2025-11-12 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_add_morning_touch_sent_at"
down_revision: Union[str, None] = "003_add_user_management_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("morning_touch_sent_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "morning_touch_sent_at", schema="public")


