from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User


class EveningReflection(Base):
    """Модель для хранения вечерней рефлексии пользователя."""

    __tablename__ = "evening_reflections"

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

    reflection_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст вечерней рефлексии"
    )

    user: Mapped["User"] = relationship(back_populates="evening_reflections")

