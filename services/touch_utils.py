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
    if course_day:
        content = repo.get_for_day(touch_type, course_day)
        if content:
            return content
    return repo.get_default(touch_type)


