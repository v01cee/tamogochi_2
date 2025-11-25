from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User


class EveningRating(Base):
    """Модель для хранения вечерних оценок пользователя."""

    __tablename__ = "evening_ratings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    rating_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    rating_energy: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Оценка уровня энергии (1-10)"
    )

    rating_happiness: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Оценка уровня счастья (1-10)"
    )

    rating_progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Оценка продвижения к результату/целям (1-10)"
    )

    user: Mapped["User"] = relationship(back_populates="evening_ratings")

