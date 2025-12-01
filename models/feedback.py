from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Feedback(Base):
    """Сообщения обратной связи от пользователей."""

    __tablename__ = "feedbacks"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Telegram ID пользователя",
    )

    username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Ник пользователя в Telegram на момент отправки",
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Имя / ФИО пользователя на момент отправки",
    )

    message_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текст сообщения обратной связи",
    )

    source: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Источник сообщения (feedback / write_to_us и т.п.)",
    )


