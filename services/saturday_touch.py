from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Tuple
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import Select, select

from core.config import settings
from core.texts import get_booking_text
from database.session import SessionLocal
from models.user import User

logger = logging.getLogger(__name__)

ACTIVE_SUBSCRIPTION_TYPES = {"trial", "paid"}


def _build_users_query() -> Select[Tuple[int, int]]:
    """Сформировать запрос на выборку активных пользователей для стратсубботы."""
    return (
        select(User.id, User.telegram_id)
        .where(User.subscription_type.in_(ACTIVE_SUBSCRIPTION_TYPES))
    )


def _fetch_users() -> List[Tuple[int, int]]:
    """Получить список активных пользователей."""
    with SessionLocal() as session:
        stmt = _build_users_query()
        result = session.execute(stmt)
        return list(result.all())


async def send_saturday_touch(bot: Bot) -> None:
    """Отправить сообщение о стратсубботе всем активным подписчикам в субботу в 12:00 МСК."""
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)
    
    # Проверяем, что сегодня суббота
    if now.weekday() != 5:  # 5 = суббота
        logger.info("Стратсуббота: сегодня не суббота, пропускаем отправку")
        return
    
    users = await asyncio.to_thread(_fetch_users)
    if not users:
        logger.info("Стратсуббота: нет пользователей для отправки")
        return

    logger.info("Стратсуббота: отправляем %s пользователям", len(users))

    # Получаем текст сообщения
    message_text = get_booking_text("saturday_reflection")
    
    # Создаем клавиатуру с кнопкой "Начать"
    keyboard_builder = InlineKeyboardBuilder()
    keyboard_builder.button(text="Начать", callback_data="saturday_reflection_start")
    keyboard_builder.adjust(1)
    keyboard = keyboard_builder.as_markup()

    async def send_to_user(telegram_id: int) -> bool:
        """Отправить сообщение одному пользователю."""
        try:
            await bot.send_message(telegram_id, message_text, reply_markup=keyboard)
            return True
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Не удалось отправить сообщение о стратсубботе пользователю %s: %s",
                telegram_id,
                exc,
            )
            return False

    # Создаем задачи для параллельной отправки
    tasks = []
    for user_id, telegram_id in users:
        task = asyncio.create_task(send_to_user(telegram_id))
        tasks.append((user_id, task))

    # Ждем завершения всех задач параллельно
    results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
    
    success_count = sum(1 for result in results if result is True and not isinstance(result, Exception))
    logger.info("Стратсуббота: отправлено %s сообщений", success_count)

