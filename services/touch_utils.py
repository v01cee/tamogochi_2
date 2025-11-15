from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from models.user import User
from repositories.touch_content_repository import TouchContentRepository


def calculate_course_day(user: User, for_date: date) -> Optional[int]:
    """
    Определить номер дня курса для пользователя.

    Начало отсчёта — subscription_started_at или subscription_paid_at.
    Включаются только будние дни (понедельник-пятница).
    """
    start_dt: Optional[datetime] = user.subscription_started_at or user.subscription_paid_at
    if not start_dt:
        return None

    start_date = start_dt.date()
    if for_date < start_date:
        return None

    day_counter = 0
    current = start_date
    while current <= for_date:
        if current.weekday() < 5:  # 0..4 — будни
            day_counter += 1
        current += timedelta(days=1)
    return day_counter


def fetch_touch_content(
    repo: TouchContentRepository,
    *,
    touch_type: str,
    course_day: Optional[int],
):
    import logging
    logger = logging.getLogger(__name__)
    
    if course_day:
        content = repo.get_for_day(touch_type, course_day)
        if content:
            logger.info(f"[TOUCH_UTILS] Найден контент для {touch_type}, день {course_day}: id={content.id}")
            return content
        else:
            logger.info(f"[TOUCH_UTILS] Контент не найден для {touch_type}, день {course_day}, пробуем дефолтный")
    else:
        logger.info(f"[TOUCH_UTILS] course_day=None для {touch_type}, пробуем дефолтный контент")
    
    # Пробуем получить дефолтный контент
    default_content = repo.get_default(touch_type)
    if default_content:
        logger.info(f"[TOUCH_UTILS] Найден дефолтный контент для {touch_type}: id={default_content.id}")
        return default_content
    
    # Если дефолтного нет, пробуем найти любой активный контент
    logger.warning(f"[TOUCH_UTILS] Дефолтный контент не найден для {touch_type}, пробуем найти любой активный контент")
    any_content = repo.get_any_active(touch_type)
    if any_content:
        logger.info(f"[TOUCH_UTILS] Найден активный контент для {touch_type}: id={any_content.id}, course_day_id={any_content.course_day_id}")
    else:
        logger.warning(f"[TOUCH_UTILS] Активный контент не найден для {touch_type}")
    return any_content


