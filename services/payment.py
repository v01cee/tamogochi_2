from __future__ import annotations

import hashlib
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import uuid4
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from core.config import settings
from models.payment import Payment
from repositories.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)

try:
    from robokassa import Merchant  # type: ignore
except ImportError:  # pragma: no cover - fallback без установленной библиотеки
    Merchant = None  # type: ignore


class PaymentService:
    """Сервис для генерации оплат через Robokassa."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = PaymentRepository(session)

    def create_payment(
        self,
        *,
        user_id: int,
        amount: Decimal,
        description: str,
        currency: str = "RUB",
    ) -> Payment:
        amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        invoice_id = uuid4().hex
        payment_url = self._build_payment_url(
            invoice_id=invoice_id,
            amount=amount,
            description=description,
            currency=currency,
        )

        payment = self.repo.create_payment(
            user_id=user_id,
            invoice_id=invoice_id,
            amount=amount,
            currency=currency,
            description=description,
            payment_url=payment_url,
        )
        return payment

    def _build_payment_url(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        description: str,
        currency: str,
    ) -> str:
        if not settings.robokassa_shop_id or not settings.robokassa_password1:
            raise RuntimeError("Robokassa credentials are not configured")

        # Пытаемся использовать официальный клиент
        if Merchant is not None:
            try:
                merchant = Merchant(
                    login=settings.robokassa_shop_id,
                    password1=settings.robokassa_password1,
                    password2=settings.robokassa_password2,
                    is_test=settings.robokassa_is_test,
                )
                payment = merchant.create_payment(
                    amount=float(amount),
                    invoice_id=invoice_id,
                    description=description,
                    currency=currency,
                    culture="ru",
                )
                payment_url = getattr(payment, "payment_url", None) or getattr(payment, "url", None)
                if payment_url:
                    return payment_url
            except Exception as exc:  # pragma: no cover - fallback
                logger.warning("Robokassa SDK failed, fallback to manual URL generation: %s", exc)

        return self._build_payment_url_manual(
            invoice_id=invoice_id,
            amount=amount,
            description=description,
            currency=currency,
        )

    def _build_payment_url_manual(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        description: str,
        currency: str,
    ) -> str:
        base_url = settings.robokassa_base_url or "https://auth.robokassa.ru/Merchant/Index.aspx"
        out_sum = f"{amount:.2f}"
        signature_parts = [
            settings.robokassa_shop_id,
            out_sum,
            invoice_id,
            settings.robokassa_password1,
        ]
        signature_source = ":".join(signature_parts)
        signature = hashlib.md5(signature_source.encode("utf-8")).hexdigest()

        params = {
            "MerchantLogin": settings.robokassa_shop_id,
            "OutSum": out_sum,
            "InvId": invoice_id,
            "Description": description,
            "SignatureValue": signature,
            "Culture": "ru",
            "Encoding": "utf-8",
        }
        if currency:
            params["OutSumCurrency"] = currency
        if settings.robokassa_is_test:
            params["IsTest"] = "1"
        if settings.robokassa_success_url:
            params["SuccessURL"] = settings.robokassa_success_url
        if settings.robokassa_fail_url:
            params["FailURL"] = settings.robokassa_fail_url

        return f"{base_url}?{urlencode(params, doseq=True)}"

    def handle_success(self, invoice_id: str) -> Optional[Payment]:
        payment = self.repo.get_by_invoice(invoice_id)
        if not payment:
            return None
        return self.repo.set_status(payment, status="paid")

    def handle_fail(self, invoice_id: str) -> Optional[Payment]:
        payment = self.repo.get_by_invoice(invoice_id)
        if not payment:
            return None
        return self.repo.set_status(payment, status="failed")

    def handle_result(
        self,
        *,
        out_sum: str,
        invoice_id: str,
        signature: str,
        robokassa_inv_id: Optional[int] = None,
    ) -> bool:
        if not self._verify_result_signature(out_sum, invoice_id, signature):
            return False

        payment = self.repo.get_by_invoice(invoice_id)
        if not payment:
            return False

        self.repo.set_status(
            payment,
            status="paid",
            robokassa_inv_id=robokassa_inv_id,
        )
        return True

    @staticmethod
    def _verify_result_signature(out_sum: str, invoice_id: str, signature: str) -> bool:
        if not settings.robokassa_password2:
            logger.error("Robokassa password2 is not configured")
            return False
        source = ":".join(
            [
                out_sum,
                invoice_id,
                settings.robokassa_password2,
            ]
        )
        calculated = hashlib.md5(source.encode("utf-8")).hexdigest().upper()
        return calculated == signature.strip().upper()

    def handle_success_redirect(self, out_sum: str, invoice_id: str, signature: str) -> bool:
        if not self._verify_success_signature(out_sum, invoice_id, signature):
            return False
        payment = self.repo.get_by_invoice(invoice_id)
        if not payment:
            return False
        self.repo.set_status(payment, status="paid")
        return True

    def handle_fail_redirect(self, invoice_id: str) -> bool:
        payment = self.repo.get_by_invoice(invoice_id)
        if not payment:
            return False
        self.repo.set_status(payment, status="failed")
        return True

    @staticmethod
    def _verify_success_signature(out_sum: str, invoice_id: str, signature: str) -> bool:
        if not settings.robokassa_password1:
            logger.error("Robokassa password1 is not configured")
            return False
        source = ":".join(
            [
                out_sum,
                invoice_id,
                settings.robokassa_password1,
            ]
        )
        calculated = hashlib.md5(source.encode("utf-8")).hexdigest().upper()
        return calculated == signature.strip().upper()


