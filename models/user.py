from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger
from database.base import Base


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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


