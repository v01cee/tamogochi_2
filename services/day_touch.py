from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import Select, func, or_, select, update

from core.config import settings
from core.texts import TEXTS
from database.session import SessionLocal
from models.touch_content import TouchContent
from models.user import User
from repositories.touch_content_repository import TouchContentRepository
from services.touch_utils import calculate_course_day, fetch_touch_content

logger = logging.getLogger(__name__)

DAY_TOUCH_TEXT_KEY = "day_touch_prompt"
ACTIVE_SUBSCRIPTION_TYPES = {"trial", "paid"}
DEFAULT_DAY_TIME = time(hour=12, minute=0)


def _build_users_query(for_date: date) -> Select[Tuple[int, int, Optional[time]]]:
    """Сформировать запрос на выборку пользователей для дневного касания."""
    return (
        select(User.id, User.telegram_id, User.day_notification_time)
        .where(User.subscription_type.in_(ACTIVE_SUBSCRIPTION_TYPES))
        .where(
            or_(
                User.day_touch_sent_at.is_(None),
                func.date(User.day_touch_sent_at) < for_date,
            )
        )
    )


def _fetch_users(for_date: date) -> List[Tuple[int, int, Optional[time]]]:
    with SessionLocal() as session:
        stmt = _build_users_query(for_date)
        result = session.execute(stmt)
        return list(result.all())


def _mark_users_sent(user_ids: List[int], sent_at: datetime) -> None:
    """Отметить пользователей как получивших дневное касание."""
    if not user_ids:
        return

    with SessionLocal() as session:
        stmt = (
            update(User)
            .where(User.id.in_(user_ids))
            .values(day_touch_sent_at=sent_at)
        )
        session.execute(stmt)
        session.commit()


async def send_day_touch(bot: Bot) -> None:
    """Отправить дневное сообщение всем активным подписчикам."""
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)
    target_date = now.date()

    users = await asyncio.to_thread(_fetch_users, target_date)
    if not users:
        logger.info("Дневное касание: нет пользователей для отправки")
        return

    logger.info("Дневное касание: отправляем %s пользователям", len(users))

    target_time = now.time().replace(second=0, microsecond=0)

    sent_user_ids: List[int] = []
    for user_id, telegram_id, user_time in users:
        effective_time = user_time or DEFAULT_DAY_TIME
        if effective_time != target_time:
            continue

        try:
            content = await asyncio.to_thread(
                _get_content_for_user,
                user_id,
                now.date(),
            )

            if not content:
                logger.warning("Нет контента для дневного касания (user %s)", user_id)
                continue

            # Отправляем summary, если есть
            if content.summary:
                await bot.send_message(telegram_id, content.summary.strip())
            
            # Отправляем ссылку на видео, если есть
            if content.video_url:
                keyboard = _build_day_keyboard()
                await bot.send_message(telegram_id, content.video_url, reply_markup=keyboard)
            else:
                # Если видео нет, отправляем клавиатуру отдельно
                keyboard = _build_day_keyboard()
                await bot.send_message(telegram_id, TEXTS.get(DAY_TOUCH_TEXT_KEY, "Стратегия дня"), reply_markup=keyboard)
            
            sent_user_ids.append(user_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Не удалось отправить дневное сообщение %s: %s", telegram_id, exc)

    await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
    logger.info("Дневное касание: отправлено %s сообщений", len(sent_user_ids))


def _build_day_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.community_chat_url:
        builder.button(text="Перейти в чат", url=settings.community_chat_url)
    builder.button(text="В меню «Стратегия дня»", callback_data="day_strategy")
    builder.adjust(1, 1)
    return builder.as_markup()


def _get_content_for_user(user_id: int, for_date: date) -> Optional[TouchContent]:
    with SessionLocal() as session:
        repo = TouchContentRepository(session)
        user = session.get(User, user_id)
        if not user:
            return repo.get_default("day")
        course_day = calculate_course_day(user, for_date)
        return fetch_touch_content(repo, touch_type="day", course_day=course_day)


