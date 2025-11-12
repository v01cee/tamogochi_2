from __future__ import annotations

from typing import Optional
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.repository import BaseRepository
from models.payment import Payment


class PaymentRepository(BaseRepository[Payment]):
    """Репозиторий для работы с платежами."""

    def __init__(self, session: Session):
        super().__init__(Payment, session)

    def get_by_invoice(self, invoice_id: str) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.invoice_id == invoice_id)
        return self.session.scalars(stmt).first()

    def create_payment(
        self,
        *,
        user_id: int,
        invoice_id: str,
        amount: Decimal,
        currency: str,
        description: str | None = None,
        payment_url: str | None = None,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            description=description,
            payment_url=payment_url,
        )
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        return payment

    def set_status(
        self,
        payment: Payment,
        *,
        status: str,
        robokassa_inv_id: int | None = None,
    ) -> Payment:
        payment.status = status
        if robokassa_inv_id is not None:
            payment.robokassa_inv_id = robokassa_inv_id
        self.session.commit()
        self.session.refresh(payment)
        return payment


