from __future__ import annotations

import logging
from typing import Optional

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from database.session import SessionLocal
from services.payment import PaymentService

logger = logging.getLogger(__name__)


def _with_session() -> SessionLocal:
    return SessionLocal()


@csrf_exempt
@require_POST
def robokassa_result(request: HttpRequest) -> HttpResponse:
    out_sum = request.POST.get("OutSum")
    invoice_id = request.POST.get("InvId") or request.POST.get("InvoiceID")
    signature = request.POST.get("SignatureValue")
    robokassa_inv_id = request.POST.get("PaymentId")

    if not out_sum or not invoice_id or not signature:
        return HttpResponseBadRequest("Missing parameters")

    session = _with_session()
    try:
        service = PaymentService(session)
        success = service.handle_result(
            out_sum=str(out_sum),
            invoice_id=str(invoice_id),
            signature=str(signature),
            robokassa_inv_id=_safe_int(robokassa_inv_id),
        )
    finally:
        session.close()

    if not success:
        logger.warning("Robokassa result validation failed for invoice %s", invoice_id)
        return HttpResponseBadRequest("Invalid signature or unknown invoice")

    return HttpResponse(f"OK{invoice_id}")


@require_GET
def robokassa_success(request: HttpRequest) -> HttpResponse:
    out_sum = request.GET.get("OutSum")
    invoice_id = request.GET.get("InvId")
    signature = request.GET.get("SignatureValue")

    if not out_sum or not invoice_id or not signature:
        return HttpResponseBadRequest("Missing parameters")

    session = _with_session()
    try:
        service = PaymentService(session)
        if not service.handle_success_redirect(str(out_sum), str(invoice_id), str(signature)):
            return HttpResponseBadRequest("Invalid signature")
    finally:
        session.close()

    return HttpResponse(
        "<h2>Оплата прошла успешно</h2><p>Вы можете закрыть окно и вернуться в бот.</p>"
    )


@require_GET
def robokassa_fail(request: HttpRequest) -> HttpResponse:
    invoice_id = request.GET.get("InvId")

    session = _with_session()
    try:
        service = PaymentService(session)
        if invoice_id:
            service.handle_fail_redirect(str(invoice_id))
    finally:
        session.close()

    return HttpResponse(
        "<h2>Платёж не завершён</h2><p>Вы можете попробовать ещё раз или написать нам.</p>",
        status=400,
    )


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


