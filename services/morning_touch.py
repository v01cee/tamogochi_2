from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import Select, func, or_, select, update

from core.config import settings
from core.texts import TEXTS
from database.session import SessionLocal
from models.touch_content import TouchContent
from models.user import User
from repositories.touch_content_repository import TouchContentRepository
from services.touch_utils import calculate_course_day, fetch_touch_content

logger = logging.getLogger(__name__)

MORNING_TOUCH_TEXT_KEY = "touch_8_1_morning_prompt"
ACTIVE_SUBSCRIPTION_TYPES = {"trial", "paid"}
DEFAULT_MORNING_TIME = time(hour=9, minute=0)


def _build_users_query(for_date: date) -> Select[Tuple[int, int, Optional[time]]]:
    """Сформировать запрос на выборку пользователей для утреннего касания."""
    return (
        select(User.id, User.telegram_id, User.morning_notification_time)
        .where(User.subscription_type.in_(ACTIVE_SUBSCRIPTION_TYPES))
        .where(
            or_(
                User.morning_touch_sent_at.is_(None),
                func.date(User.morning_touch_sent_at) < for_date,
            )
        )
    )


def _fetch_users(for_date: date) -> List[Tuple[int, int, Optional[time]]]:
    with SessionLocal() as session:
        stmt = _build_users_query(for_date)
        result = session.execute(stmt)
        return list(result.all())


def _mark_users_sent(user_ids: Iterable[int], sent_at: datetime) -> None:
    ids = list(user_ids)
    if not ids:
        return

    with SessionLocal() as session:
        stmt = (
            update(User)
            .where(User.id.in_(ids))
            .values(morning_touch_sent_at=sent_at)
        )
        session.execute(stmt)
        session.commit()


async def send_morning_touch(bot: Bot) -> None:
    """Отправить утреннее сообщение всем активным подписчикам."""
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)
    target_date = now.date()

    users = await asyncio.to_thread(_fetch_users, target_date)
    if not users:
        logger.info("Утреннее касание: нет пользователей для отправки")
        return

    logger.info("Утреннее касание: отправляем %s пользователям", len(users))

    target_time = now.time().replace(second=0, microsecond=0)

    sent_user_ids: List[int] = []
    for user_id, telegram_id, user_time in users:
        effective_time = user_time or DEFAULT_MORNING_TIME
        if effective_time != target_time:
            continue
        try:
            content = await asyncio.to_thread(
                _get_content_for_user,
                user_id,
                now.date(),
            )

            if content:
                await _send_touch_content(bot, telegram_id, content)
            await bot.send_message(telegram_id, TEXTS[MORNING_TOUCH_TEXT_KEY])
            sent_user_ids.append(user_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Не удалось отправить утреннее сообщение пользователю %s: %s",
                telegram_id,
                exc,
            )

    await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
    logger.info("Утреннее касание: отправлено %s сообщений", len(sent_user_ids))


async def _send_touch_content(bot: Bot, telegram_id: int, content: TouchContent) -> None:
    """Отправить пользователю материалы касания."""
    header_parts = [
        part for part in (content.step_code, content.title) if part
    ]
    header = " — ".join(header_parts)

    if content.video_file_path:
        file_path = Path(settings.media_root) / content.video_file_path
        caption_parts = [header, content.summary]
        caption = "\n\n".join(part.strip() for part in caption_parts if part and part.strip())
        if file_path.exists():
            await bot.send_video(
                telegram_id,
                FSInputFile(file_path),
                caption=caption or None,
            )
        else:
            logger.warning("Файл видео касания не найден: %s", file_path)
            if content.video_url:
                await bot.send_video(telegram_id, content.video_url, caption=caption or None)
    elif content.video_url:
        caption_parts = [header, content.summary]
        caption = "\n\n".join(part.strip() for part in caption_parts if part and part.strip())
        await bot.send_video(telegram_id, content.video_url, caption=caption or None)
    else:
        text_parts = [header, content.summary]
        text = "\n\n".join(part.strip() for part in text_parts if part and part.strip())
        if text:
            await bot.send_message(telegram_id, text)

    if content.transcript:
        await bot.send_message(telegram_id, content.transcript.strip())

    if content.questions:
        await bot.send_message(telegram_id, content.questions.strip())


def _get_content_for_user(user_id: int, for_date: date) -> Optional[TouchContent]:
    with SessionLocal() as session:
        repo = TouchContentRepository(session)
        user = session.get(User, user_id)
        if not user:
            return repo.get_default("morning")
        course_day = calculate_course_day(user, for_date)
        return fetch_touch_content(repo, touch_type="morning", course_day=course_day)


