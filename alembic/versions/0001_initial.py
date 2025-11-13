"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-12 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language_code", sa.String(length=10), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("subscription_type", sa.String(length=50), nullable=True),
        sa.Column("subscription_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("morning_touch_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_intro_seen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_first_visit", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("morning_notification_time", sa.Time(timezone=False), nullable=True),
        sa.Column("day_notification_time", sa.Time(timezone=False), nullable=True),
        sa.Column("evening_notification_time", sa.Time(timezone=False), nullable=True),
        schema="public",
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True, schema="public")
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False, schema="public")

    op.create_table(
        "course_days",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("day_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        schema="public",
    )

    op.create_table(
        "touch_contents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("course_day_id", sa.Integer(), sa.ForeignKey("public.course_days.id", ondelete="SET NULL"), nullable=True),
        sa.Column("touch_type", sa.String(length=20), nullable=False),
        sa.Column("step_code", sa.String(length=50), nullable=True, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("video_file_path", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("questions", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        schema="public",
    )
    op.create_index("ix_touch_contents_touch_type", "touch_contents", ["touch_type"], unique=False, schema="public")
    op.create_index("ix_touch_contents_course_day_id", "touch_contents", ["course_day_id"], unique=False, schema="public")

    op.create_table(
        "quiz_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("energy", sa.Integer(), nullable=False),
        sa.Column("happiness", sa.Integer(), nullable=False),
        sa.Column("sleep_quality", sa.Integer(), nullable=False),
        sa.Column("relationships_quality", sa.Integer(), nullable=False),
        sa.Column("life_balance", sa.Integer(), nullable=False),
        sa.Column("strategy_level", sa.Integer(), nullable=False),
        schema="public",
    )
    op.create_index("ix_quiz_results_user_id", "quiz_results", ["user_id"], unique=False, schema="public")
    op.create_index("ix_quiz_results_is_active", "quiz_results", ["is_active"], unique=False, schema="public")

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="RUB"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("payment_url", sa.String(length=1024), nullable=True),
        sa.Column("robokassa_inv_id", sa.Integer(), nullable=True),
        schema="public",
    )
    op.create_index("ix_payments_status", "payments", ["status"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_payments_status", table_name="payments", schema="public")
    op.drop_table("payments", schema="public")

    op.drop_index("ix_quiz_results_is_active", table_name="quiz_results", schema="public")
    op.drop_index("ix_quiz_results_user_id", table_name="quiz_results", schema="public")
    op.drop_table("quiz_results", schema="public")

    op.drop_index("ix_touch_contents_course_day_id", table_name="touch_contents", schema="public")
    op.drop_index("ix_touch_contents_touch_type", table_name="touch_contents", schema="public")
    op.drop_table("touch_contents", schema="public")

    op.drop_table("course_days", schema="public")

    op.drop_index("ix_users_is_active", table_name="users", schema="public")
    op.drop_index("ix_users_telegram_id", table_name="users", schema="public")
    op.drop_table("users", schema="public")


