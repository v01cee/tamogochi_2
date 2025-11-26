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

# from core.config import settings
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
    try:
        tz = ZoneInfo("Europe/Moscow")
        now = datetime.now(tz=tz)
        target_date = now.date()

        # Получаем bot_id один раз (с обработкой сетевых ошибок)
        try:
            bot_info = await bot.get_me()
            bot_id = bot_info.id
        except Exception as e:
            logger.error("Не удалось получить bot_id (сетевые проблемы): %s", e)
            return

        users = await asyncio.to_thread(_fetch_users, target_date)
        if not users:
            logger.info("Утреннее касание: нет пользователей для отправки")
            return

        logger.info("Утреннее касание: отправляем %s пользователям", len(users))

        target_time = now.time().replace(second=0, microsecond=0)

        # Фильтруем пользователей по времени
        filtered_users = [
            (user_id, telegram_id)
            for user_id, telegram_id, user_time in users
            if (user_time or DEFAULT_MORNING_TIME) == target_time
        ]

        if not filtered_users:
            logger.info("Утреннее касание: нет пользователей для отправки в это время")
            return

        logger.info("Утреннее касание: отправляем %s пользователям (после фильтрации по времени)", len(filtered_users))

        async def send_to_user(user_id: int, telegram_id: int) -> bool:
            """Отправить сообщение одному пользователю."""
            try:
                content = await asyncio.to_thread(
                    _get_content_for_user,
                    user_id,
                    now.date(),
                )

                if content:
                    await _send_touch_content(bot, telegram_id, content, bot_id=bot_id)
                return True
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "Не удалось отправить утреннее сообщение пользователю %s: %s",
                    telegram_id,
                    exc,
                )
                return False

        # Создаем задачи для параллельной отправки (limited-aiogram автоматически контролирует лимиты)
        sent_user_ids: List[int] = []
        tasks = []
        
        for user_id, telegram_id in filtered_users:
            # Создаем задачу для отправки
            task = asyncio.create_task(send_to_user(user_id, telegram_id))
            tasks.append((user_id, task))

        # Ждем завершения всех задач параллельно
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (user_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("Ошибка при отправке пользователю %s: %s", user_id, result)
            elif result is True:
                sent_user_ids.append(user_id)

        await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
        logger.info("Утреннее касание: отправлено %s сообщений", len(sent_user_ids))
    except Exception as exc:
        logger.error("Критическая ошибка в send_morning_touch: %s", exc, exc_info=True)


async def _send_touch_content(bot: Bot, telegram_id: int, content: TouchContent, bot_id: int = None) -> None:
    """Отправить пользователю материалы касания."""
    import redis
    import json
    
    # Получаем bot_id если не передан
    if bot_id is None:
        bot_info = await bot.get_me()
        bot_id = bot_info.id
    
    # Формируем caption: описание (summary) отправляется как текст к видео
    caption = content.summary.strip() if content.summary else None
    
    # Отправляем видео с описанием в caption
    video_sent = False
    if content.video_file_path:
        file_path = Path("media") / content.video_file_path
        if file_path.exists():
            await bot.send_video(
                telegram_id,
                FSInputFile(file_path),
                caption=caption,
            )
            video_sent = True
        else:
            logger.warning("Файл видео касания не найден: %s", file_path)
            if content.video_url:
                await bot.send_video(telegram_id, content.video_url, caption=caption)
                video_sent = True
    elif content.video_url:
        await bot.send_video(telegram_id, content.video_url, caption=caption)
        video_sent = True
    
    # Если видео нет - отправляем только описание
    if not video_sent:
        if content.summary:
            await bot.send_message(telegram_id, content.summary.strip())
    
    # После отправки видео/описания отправляем фиксированный текст
    await bot.send_message(
        telegram_id,
        "Пожалуйста, ответь на эти вопросы — напиши или наговори голосом свои мысли. Мы соберём их в твою личную карту стратегий"
    )
    
    # Через 5 секунд отправляем первый вопрос из поля "Вопросы"
    if content.questions:
        await asyncio.sleep(5)
        
        # Разделяем вопросы по переносу строки
        questions_text = content.questions.strip()
        split_lines = questions_text.split('\n')
        questions_list = [line.strip() for line in split_lines if line.strip()]
        
        if questions_list:
            first_question = questions_list[0]
            await bot.send_message(telegram_id, first_question)
            
            # Сохраняем состояние и данные в Redis для обработки ответов
            from core.config import settings
            
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
            
            state_key = f"fsm:{bot_id}:{telegram_id}:state"
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            
            # Сохраняем состояние для обработки вопросов касания
            redis_client.set(state_key, "TouchQuestionStates:waiting_for_answer", ex=3600)
            
            # Сохраняем данные о вопросах
            redis_data = {
                "touch_content_id": content.id,
                "questions_list": questions_list,
                "current_question_index": 0,
                "answers": []
            }
            redis_client.set(data_key, json.dumps(redis_data), ex=3600)
            
            logger.info(f"[MORNING_TOUCH] Отправлен первый вопрос для пользователя {telegram_id}, всего вопросов: {len(questions_list)}")


def _get_content_for_user(user_id: int, for_date: date) -> Optional[TouchContent]:
    with SessionLocal() as session:
        repo = TouchContentRepository(session)
        user = session.get(User, user_id)
        if not user:
            return repo.get_default("morning")
        course_day = calculate_course_day(user, for_date)
        return fetch_touch_content(repo, touch_type="morning", course_day=course_day)


