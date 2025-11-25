"""add_touch_answers_evening_reflections_ratings_saturday

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-20 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем таблицу touch_answers
    op.create_table(
        "touch_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("touch_content_id", sa.Integer(), nullable=False),
        sa.Column("touch_date", sa.Date(), nullable=False),
        sa.Column("question_index", sa.Integer(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["touch_content_id"], ["touch_contents.id"], ondelete="CASCADE"),
        sa.Index("ix_touch_answers_user_id", "user_id"),
        sa.Index("ix_touch_answers_touch_content_id", "touch_content_id"),
        sa.Index("ix_touch_answers_touch_date", "touch_date"),
        sa.Index("ix_touch_answers_user_id_touch_content_id_touch_date", "user_id", "touch_content_id", "touch_date"),
    )

    # Создаем таблицу evening_reflections
    op.create_table(
        "evening_reflections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reflection_date", sa.Date(), nullable=False),
        sa.Column("reflection_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.Index("ix_evening_reflections_user_id", "user_id"),
        sa.Index("ix_evening_reflections_reflection_date", "reflection_date"),
    )

    # Создаем таблицу evening_ratings
    op.create_table(
        "evening_ratings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rating_date", sa.Date(), nullable=False),
        sa.Column("rating_energy", sa.Integer(), nullable=False),
        sa.Column("rating_happiness", sa.Integer(), nullable=False),
        sa.Column("rating_progress", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.Index("ix_evening_ratings_user_id", "user_id"),
        sa.Index("ix_evening_ratings_rating_date", "rating_date"),
    )

    # Создаем таблицу saturday_reflections
    op.create_table(
        "saturday_reflections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reflection_date", sa.Date(), nullable=False),
        sa.Column("segment_1", sa.Text(), nullable=True, comment="1/5 Похвастаться"),
        sa.Column("segment_2", sa.Text(), nullable=True, comment="2/5 Что не получилось"),
        sa.Column("segment_3", sa.Text(), nullable=True, comment="3/5 Поблагодарить"),
        sa.Column("segment_4", sa.Text(), nullable=True, comment="4/5 Помечтать"),
        sa.Column("segment_5", sa.Text(), nullable=True, comment="5/5 Пообещать"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.Index("ix_saturday_reflections_user_id", "user_id"),
        sa.Index("ix_saturday_reflections_reflection_date", "reflection_date"),
    )


def downgrade() -> None:
    op.drop_table("saturday_reflections")
    op.drop_table("evening_ratings")
    op.drop_table("evening_reflections")
    op.drop_table("touch_answers")

