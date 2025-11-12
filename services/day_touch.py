from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import Select, func, or_, select

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
    return (
        select(User.id, User.telegram_id, User.day_notification_time)
        .where(User.subscription_type.in_(ACTIVE_SUBSCRIPTION_TYPES))
        .where(
            or_(
                User.subscription_started_at.is_not(None),
                User.subscription_paid_at.is_not(None),
            )
        )
        .where(
            or_(
                User.subscription_type == "trial",
                User.subscription_type == "free_week",
                User.subscription_type == "monthly",
                User.subscription_type == "paid",
            )
        )
    )


def _fetch_users(for_date: date) -> List[Tuple[int, int, Optional[time]]]:
    with SessionLocal() as session:
        stmt = _build_users_query(for_date)
        result = session.execute(stmt)
        return list(result.all())


async def send_day_touch(bot: Bot) -> None:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)
    target_date = now.date()

    users = await asyncio.to_thread(_fetch_users, target_date)
    if not users:
        return

    target_time = now.time().replace(second=0, microsecond=0)

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
                logger.warning("Нет контента для дневного касания (day %s)", user_id)
                continue

            keyboard = _build_day_keyboard()
            await bot.send_message(telegram_id, TEXTS[DAY_TOUCH_TEXT_KEY], reply_markup=keyboard)
            if content.video_url:
                await bot.send_message(telegram_id, content.video_url)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Не удалось отправить дневное сообщение %s: %s", telegram_id, exc)


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


