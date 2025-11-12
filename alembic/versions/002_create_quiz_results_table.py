"""Create quiz_results table

Revision ID: 002
Revises: 001
Create Date: 2025-11-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quiz_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("happiness", sa.Integer(), nullable=False),
        sa.Column("sleep_quality", sa.Integer(), nullable=False),
        sa.Column("relationships_quality", sa.Integer(), nullable=False),
        sa.Column("life_balance", sa.Integer(), nullable=False),
        sa.Column("strategy_level", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        "ix_quiz_results_id",
        "quiz_results",
        ["id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_quiz_results_user_id",
        "quiz_results",
        ["user_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_quiz_results_is_active",
        "quiz_results",
        ["is_active"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_quiz_results_is_active", table_name="quiz_results", schema="public")
    op.drop_index("ix_quiz_results_user_id", table_name="quiz_results", schema="public")
    op.drop_index("ix_quiz_results_id", table_name="quiz_results", schema="public")
    op.drop_table("quiz_results", schema="public")



