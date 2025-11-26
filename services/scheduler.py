from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from core.config import settings
from services.morning_touch import send_morning_touch
from services.day_touch import send_day_touch
from services.evening_touch import send_evening_touch
from services.saturday_touch import send_saturday_touch
from services.qwen_warmup import warmup_whisper_model, keep_whisper_warm

logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Настроить планировщик фоновых задач."""
    scheduler = AsyncIOScheduler(timezone=settings.timezone)

    scheduler.add_job(
        send_morning_touch,
        trigger=CronTrigger(minute="*", second=0),
        kwargs={"bot": bot},
        name="morning_touch",
        id="morning_touch",
        replace_existing=True,
        max_instances=1,  # Не запускать новый экземпляр, если предыдущий еще выполняется
    )

    scheduler.add_job(
        send_day_touch,
        trigger=CronTrigger(minute="*", second=0),
        kwargs={"bot": bot},
        name="day_touch",
        id="day_touch",
        replace_existing=True,
        max_instances=1,  # Не запускать новый экземпляр, если предыдущий еще выполняется
    )

    scheduler.add_job(
        send_evening_touch,
        trigger=CronTrigger(minute="*", second=0),
        kwargs={"bot": bot},
        name="evening_touch",
        id="evening_touch",
        replace_existing=True,
        max_instances=1,  # Не запускать новый экземпляр, если предыдущий еще выполняется
    )

    # Стратсуббота: отправка сообщения о рефлексии в субботу в 12:00 МСК
    scheduler.add_job(
        send_saturday_touch,
        trigger=CronTrigger(day_of_week="sat", hour=12, minute=0),
        kwargs={"bot": bot},
        name="saturday_touch",
        id="saturday_touch",
        replace_existing=True,
    )

    # Прогрев модели Whisper при старте (одноразовая задача через 20 секунд)
    tz = ZoneInfo(settings.timezone)
    whisper_warmup_time = datetime.now(tz=tz) + timedelta(seconds=20)
    
    scheduler.add_job(
        warmup_whisper_model,
        trigger=DateTrigger(run_date=whisper_warmup_time),
        id="whisper_warmup_startup",
        replace_existing=True,
        max_instances=1,
    )

    # Keep-alive для Whisper каждые 15 минут (реже, чем Qwen, так как используется реже)
    scheduler.add_job(
        keep_whisper_warm,
        trigger=CronTrigger(minute="*/15"),  # Каждые 15 минут
        id="whisper_keep_alive",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Планировщик задач запущен (часовой пояс %s)", settings.timezone)
    logger.info("📅 Стратсуббота: отправка сообщения о рефлексии каждую субботу в 12:00 МСК")
    logger.info("🎤 Запланирован прогрев модели Whisper через 20 секунд после старта")
    logger.info("🎤 Keep-alive для модели Whisper каждые 15 минут")
    
    return scheduler


