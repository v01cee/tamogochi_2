"""Add user management fields

Revision ID: 003
Revises: 002
Create Date: 2025-11-11 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True), schema="public")
    op.add_column("users", sa.Column("role", sa.String(length=255), nullable=True), schema="public")
    op.add_column("users", sa.Column("company", sa.String(length=255), nullable=True), schema="public")
    op.add_column("users", sa.Column("subscription_type", sa.String(length=50), nullable=True), schema="public")
    op.add_column(
        "users",
        sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("subscription_paid_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "users",
        sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("users", "consent_accepted_at", schema="public")
    op.drop_column("users", "subscription_paid_at", schema="public")
    op.drop_column("users", "subscription_started_at", schema="public")
    op.drop_column("users", "subscription_type", schema="public")
    op.drop_column("users", "company", schema="public")
    op.drop_column("users", "role", schema="public")
    op.drop_column("users", "full_name", schema="public")



