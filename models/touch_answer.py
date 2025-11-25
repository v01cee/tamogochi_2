from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, Date, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User
    from models.touch_content import TouchContent


class TouchAnswer(Base):
    """Модель для хранения ответов пользователей на вопросы касаний (утро/день/вечер)."""

    __tablename__ = "touch_answers"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    touch_content_id: Mapped[int] = mapped_column(
        ForeignKey("touch_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    touch_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    question_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Индекс вопроса (0, 1, 2, ...)"
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст ответа пользователя"
    )

    user: Mapped["User"] = relationship(back_populates="touch_answers")
    touch_content: Mapped["TouchContent"] = relationship()

