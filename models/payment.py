from __future__ import annotations

from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.user import User


class Payment(Base):
    """Платёж пользователя через Robokassa."""

    __tablename__ = "payments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    payment_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    robokassa_inv_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")


