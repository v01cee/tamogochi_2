from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

logger = logging.getLogger(__name__)


async def _safe_telegram_call(
    action: str,
    chat_id: int | str,
    call: Callable[[], Awaitable[Any]],
    *,
    max_attempts: int = 3,
) -> Any:
    """
    Универсальная обёртка с повторными попытками для вызовов Telegram API.

    Args:
        action: описание действия (send_message, send_video и т.д.)
        chat_id: идентификатор чата / пользователя
        call: корутина, совершающая реальный вызов Telegram API
        max_attempts: количество попыток (не включает RetryAfter, т.к. он повторяется без уменьшения счётчика)
    """
    attempt = 1
    while True:
        try:
            return await call()
        except TelegramRetryAfter as exc:
            wait_time = exc.retry_after + 1
            logger.warning(
                "Telegram просит подождать перед '%s' для chat_id=%s. Ждём %s секунд",
                action,
                chat_id,
                wait_time,
            )
            await asyncio.sleep(wait_time)
            continue
        except TelegramForbiddenError:
            logger.warning(
                "Telegram запретил '%s' для chat_id=%s. Вероятно, пользователь заблокировал бота или удалил чат",
                action,
                chat_id,
            )
            return None
        except TelegramBadRequest as exc:
            logger.error(
                "Некорректный запрос при '%s' для chat_id=%s: %s",
                action,
                chat_id,
                exc,
            )
            if attempt >= max_attempts:
                raise
        except TelegramAPIError as exc:
            logger.error(
                "Telegram API error (%s) при '%s' для chat_id=%s (попытка %s/%s)",
                exc.__class__.__name__,
                action,
                chat_id,
                attempt,
                max_attempts,
            )
            if attempt >= max_attempts:
                raise
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(
                "Неизвестная ошибка при '%s' для chat_id=%s: %s",
                action,
                chat_id,
                exc,
                exc_info=True,
            )
            if attempt >= max_attempts:
                raise

        attempt += 1
        backoff = min(2 * attempt, 10)
        await asyncio.sleep(backoff)


class SafeBot(Bot):
    """Расширение Bot с повторными попытками при отправке сообщений/медиа."""

    async def send_message(self, chat_id: int | str, text: str, **kwargs: Any) -> Any:  # type: ignore[override]
        return await _safe_telegram_call(
            "send_message",
            chat_id,
            lambda: super().send_message(chat_id, text, **kwargs),
        )

    async def send_video(self, chat_id: int | str, video: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        return await _safe_telegram_call(
            "send_video",
            chat_id,
            lambda: super().send_video(chat_id, video, **kwargs),
        )



