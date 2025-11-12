"""create touch contents table

Revision ID: 007_create_touch_contents_table
Revises: 006_add_is_first_visit_flag
Create Date: 2025-11-12 00:40:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "007_create_touch_contents_table"
down_revision: Union[str, None] = "006_add_is_first_visit_flag"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_days",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("day_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="public",
    )

    course_day_table = sa.table(
        "course_days",
        sa.column("day_number", sa.Integer),
        sa.column("title", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(
        course_day_table,
        [
            {"day_number": day, "title": f"День {day}", "is_active": True}
            for day in range(1, 25)
        ],
    )

    op.create_table(
        "touch_contents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "course_day_id",
            sa.Integer(),
            sa.ForeignKey("public.course_days.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("touch_type", sa.String(length=20), nullable=False),
        sa.Column("step_code", sa.String(length=50), nullable=True, unique=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("video_file_path", sa.String(length=500), nullable=True),
        sa.Column("video_url", sa.String(length=500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("questions", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        schema="public",
    )
    op.create_index(
        "ix_touch_contents_touch_type",
        "touch_contents",
        ["touch_type"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_touch_contents_course_day_id",
        "touch_contents",
        ["course_day_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_touch_contents_course_day_id", table_name="touch_contents", schema="public")
    op.drop_index("ix_touch_contents_touch_type", table_name="touch_contents", schema="public")
    op.drop_table("touch_contents", schema="public")
    op.drop_table("course_days", schema="public")


