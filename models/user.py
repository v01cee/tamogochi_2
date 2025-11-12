from __future__ import annotations

from datetime import datetime, time
from typing import List, TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, DateTime, Boolean, Time
from database.base import Base

if TYPE_CHECKING:
    from models.payment import Payment
    from models.quiz_result import QuizResult


class User(Base):
    """Модель пользователя Telegram"""

    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    language_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    company: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    subscription_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    subscription_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    subscription_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    consent_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    morning_touch_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    notification_intro_seen: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    is_first_visit: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    morning_notification_time: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
    )

    day_notification_time: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
    )

    evening_notification_time: Mapped[time | None] = mapped_column(
        Time(timezone=False),
        nullable=True,
    )

    quiz_results: Mapped[List["QuizResult"]] = relationship(
        "QuizResult",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


