from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User


class QuizResult(Base):
    """Результаты стартового опроса пользователя."""

    __tablename__ = "quiz_results"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    energy: Mapped[int] = mapped_column(Integer, nullable=False)
    happiness: Mapped[int] = mapped_column(Integer, nullable=False)
    sleep_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    relationships_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    life_balance: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy_level: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship(back_populates="quiz_results")



