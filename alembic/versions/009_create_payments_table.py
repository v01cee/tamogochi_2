"""create payments table

Revision ID: 009_create_payments_table
Revises: 008_add_notification_times
Create Date: 2025-11-12 01:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009_create_payments_table"
down_revision: Union[str, None] = "008_add_notification_times"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("invoice_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="RUB"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("payment_url", sa.String(length=1024), nullable=True),
        sa.Column("robokassa_inv_id", sa.Integer(), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_payments_status",
        "payments",
        ["status"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments", schema="public")
    op.drop_table("payments", schema="public")


