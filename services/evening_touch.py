from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import Select, func, or_, select, update
import redis
import json

from core.config import settings
from core.texts import TEXTS
from database.session import SessionLocal
from models.touch_content import TouchContent
from models.user import User
from repositories.touch_content_repository import TouchContentRepository
from services.touch_utils import calculate_course_day, fetch_touch_content
from core.states import EveningRatingStates

logger = logging.getLogger(__name__)

EVENING_TOUCH_TEXT_KEY = "evening_touch_prompt"
ACTIVE_SUBSCRIPTION_TYPES = {"trial", "paid"}
DEFAULT_EVENING_TIME = time(hour=21, minute=0)


def _build_users_query(for_date: date) -> Select[Tuple[int, int, Optional[time]]]:
    """Сформировать запрос на выборку пользователей для вечернего касания."""
    return (
        select(User.id, User.telegram_id, User.evening_notification_time)
        .where(User.subscription_type.in_(ACTIVE_SUBSCRIPTION_TYPES))
        .where(
            or_(
                User.evening_touch_sent_at.is_(None),
                func.date(User.evening_touch_sent_at) < for_date,
            )
        )
    )


def _fetch_users(for_date: date) -> List[Tuple[int, int, Optional[time]]]:
    with SessionLocal() as session:
        stmt = _build_users_query(for_date)
        result = session.execute(stmt)
        return list(result.all())


def _mark_users_sent(user_ids: List[int], sent_at: datetime) -> None:
    """Отметить пользователей как получивших вечернее касание."""
    if not user_ids:
        return

    with SessionLocal() as session:
        stmt = (
            update(User)
            .where(User.id.in_(user_ids))
            .values(evening_touch_sent_at=sent_at)
        )
        session.execute(stmt)
        session.commit()


async def send_evening_touch(bot: Bot) -> None:
    """Отправить вечернее сообщение всем активным подписчикам."""
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz=tz)
    target_date = now.date()
    
    # Получаем bot_id один раз
    bot_info = await bot.get_me()
    bot_id = bot_info.id

    users = await asyncio.to_thread(_fetch_users, target_date)
    if not users:
        logger.info("Вечернее касание: нет пользователей для отправки")
        return

    logger.info("Вечернее касание: отправляем %s пользователям", len(users))

    target_time = now.time().replace(second=0, microsecond=0)

    sent_user_ids: List[int] = []
    for user_id, telegram_id, user_time in users:
        effective_time = user_time or DEFAULT_EVENING_TIME
        if effective_time != target_time:
            continue

        try:
            content = await asyncio.to_thread(
                _get_content_for_user,
                user_id,
                now.date(),
            )

            if not content:
                logger.warning("Нет контента для вечернего касания (user %s)", user_id)
                continue

            # Отправляем видео или описание
            await _send_evening_content(bot, telegram_id, content)
            
            # Отправляем первый вопрос оценки
            await _send_first_rating_question(bot, telegram_id, bot_id=bot_id, touch_content_id=content.id)
            
            sent_user_ids.append(user_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Не удалось отправить вечернее сообщение %s: %s", telegram_id, exc)

    await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
    logger.info("Вечернее касание: отправлено %s сообщений", len(sent_user_ids))


async def _send_evening_content(bot: Bot, telegram_id: int, content: TouchContent) -> None:
    """Отправить пользователю видео или описание для вечернего касания."""
    caption = content.summary.strip() if content.summary else None
    
    # Если есть видео - отправляем видео с caption
    video_file_path = getattr(content, 'video_file_path', None)
    if video_file_path:
        file_path = Path(settings.media_root) / video_file_path
        if file_path.exists():
            await bot.send_video(
                telegram_id,
                FSInputFile(file_path),
                caption=caption,
            )
            return
        else:
            logger.warning("Файл видео касания не найден: %s", file_path)
            # Если файл не найден, пробуем URL
            if content.video_url:
                await bot.send_message(telegram_id, content.video_url)
                if caption:
                    await bot.send_message(telegram_id, caption)
                return
    
    # Если есть video_url, но нет файла
    if content.video_url:
        await bot.send_message(telegram_id, content.video_url)
        if caption:
            await bot.send_message(telegram_id, caption)
        return
    
    # Если видео нет - отправляем только описание
    if content.summary:
        await bot.send_message(telegram_id, content.summary.strip())


def _build_evening_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if settings.community_chat_url:
        builder.button(text="Перейти в чат", url=settings.community_chat_url)
    builder.button(text="В меню «Стратегия дня»", callback_data="day_strategy")
    builder.button(text="В главное меню", callback_data="back_to_menu")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


async def _send_first_rating_question(bot: Bot, telegram_id: int, bot_id: int = None, touch_content_id: int = None) -> None:
    """Отправить первый вопрос оценки для вечернего касания."""
    # Получаем bot_id если не передан
    if bot_id is None:
        bot_info = await bot.get_me()
        bot_id = bot_info.id
    
    # Создаем клавиатуру с кнопками 1-10
    keyboard_builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        keyboard_builder.button(text=str(i), callback_data=f"evening_rating_{i}")
    keyboard_builder.adjust(5, 5)  # 2 ряда по 5 кнопок
    keyboard = keyboard_builder.as_markup()
    
    # Отправляем первый вопрос
    question_text = "1/5 Оцените уровень энергии"
    await bot.send_message(telegram_id, question_text, reply_markup=keyboard)
    
    # Сохраняем состояние в Redis
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=settings.redis_db,
        decode_responses=True
    )
    
    state_key = f"fsm:{bot_id}:{telegram_id}:state"
    data_key = f"fsm:{bot_id}:{telegram_id}:data"
    
    # Сохраняем состояние
    redis_client.set(state_key, "EveningRatingStates:rating_energy", ex=3600)  # 1 час
    
    # Сохраняем данные (включая touch_content_id для последующей отправки вопросов)
    redis_data = {
        "touch_content_id": touch_content_id,
        "rating_energy": None,
        "rating_happiness": None,
        "rating_progress": None,
        "rating_question_4": None,
        "rating_question_5": None,
        "current_question": 1
    }
    redis_client.set(data_key, json.dumps(redis_data), ex=3600)


def _get_content_for_user(user_id: int, for_date: date) -> Optional[TouchContent]:
    with SessionLocal() as session:
        repo = TouchContentRepository(session)
        user = session.get(User, user_id)
        if not user:
            return repo.get_default("evening")
        course_day = calculate_course_day(user, for_date)
        return fetch_touch_content(repo, touch_type="evening", course_day=course_day)


