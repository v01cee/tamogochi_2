from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings
from services.morning_touch import send_morning_touch
from services.day_touch import send_day_touch
from services.evening_touch import send_evening_touch

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
    )

    scheduler.add_job(
        send_day_touch,
        trigger=CronTrigger(minute="*", second=0),
        kwargs={"bot": bot},
        name="day_touch",
        id="day_touch",
        replace_existing=True,
    )

    scheduler.add_job(
        send_evening_touch,
        trigger=CronTrigger(minute="*", second=0),
        kwargs={"bot": bot},
        name="evening_touch",
        id="evening_touch",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Планировщик задач запущен (часовой пояс %s)", settings.timezone)
    return scheduler


