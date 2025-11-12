"""add is_first_visit flag to users

Revision ID: 006_add_is_first_visit_flag
Revises: 005_add_notification_intro_seen
Create Date: 2025-11-12 00:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_add_is_first_visit_flag"
down_revision: Union[str, None] = "005_add_notification_intro_seen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_first_visit",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "is_first_visit", schema="public")


