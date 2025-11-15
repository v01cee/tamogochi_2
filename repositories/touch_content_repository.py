from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.repository import BaseRepository
from models.course_day import CourseDay
from models.touch_content import TouchContent


class TouchContentRepository(BaseRepository[TouchContent]):
    """Репозиторий для работы с контентом касаний."""

    def __init__(self, session: Session):
        super().__init__(TouchContent, session)

    def get_for_day(self, touch_type: str, day_number: int) -> Optional[TouchContent]:
        stmt = (
            select(TouchContent)
            .join(CourseDay, TouchContent.course_day_id == CourseDay.id, isouter=True)
            .where(
                TouchContent.touch_type == touch_type,
                TouchContent.is_active.is_(True),
                CourseDay.day_number == day_number,
                CourseDay.is_active.is_(True),
            )
            .order_by(
                TouchContent.order_index.asc(),
                TouchContent.updated_at.desc(),
            )
        )
        return self.session.scalars(stmt).first()

    def get_default(self, touch_type: str) -> Optional[TouchContent]:
        stmt = (
            select(TouchContent)
            .where(
                TouchContent.touch_type == touch_type,
                TouchContent.is_active.is_(True),
                TouchContent.course_day_id.is_(None),
            )
            .order_by(
                TouchContent.order_index.asc(),
                TouchContent.updated_at.desc(),
            )
        )
        return self.session.scalars(stmt).first()
    
    def get_any_active(self, touch_type: str) -> Optional[TouchContent]:
        """Получить любой активный контент для touch_type, если дефолтного нет."""
        stmt = (
            select(TouchContent)
            .where(
                TouchContent.touch_type == touch_type,
                TouchContent.is_active.is_(True),
            )
            .order_by(
                TouchContent.order_index.asc(),
                TouchContent.updated_at.desc(),
            )
        )
        return self.session.scalars(stmt).first()


