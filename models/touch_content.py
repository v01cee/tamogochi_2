from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class TouchContent(Base):
    """Контент для касаний (утро/день/вечер)."""

    __tablename__ = "touch_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_day_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("course_days.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    touch_type: Mapped[str] = mapped_column(String(20), index=True)
    step_code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    video_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    questions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TouchContent(id={self.id}, type={self.touch_type}, step_code={self.step_code})>"


