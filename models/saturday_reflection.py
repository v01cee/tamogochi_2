from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User


class SaturdayReflection(Base):
    """Модель для хранения ответов на рефлексию стратсубботы."""

    __tablename__ = "saturday_reflections"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reflection_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    segment_1: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="1/5 Похвастаться"
    )

    segment_2: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="2/5 Что не получилось"
    )

    segment_3: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="3/5 Поблагодарить"
    )

    segment_4: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="4/5 Помечтать"
    )

    segment_5: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="5/5 Пообещать"
    )

    user: Mapped["User"] = relationship(back_populates="saturday_reflections")

