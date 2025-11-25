from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.repository import BaseRepository
from models.saturday_reflection import SaturdayReflection


class SaturdayReflectionRepository(BaseRepository[SaturdayReflection]):
    """Репозиторий для рефлексий стратсубботы."""

    def __init__(self, session: Session):
        super().__init__(SaturdayReflection, session)

    def get_by_user_and_date(
        self,
        user_id: int,
        reflection_date: date
    ) -> Optional[SaturdayReflection]:
        """Получить рефлексию пользователя за конкретную дату."""
        return self.session.query(SaturdayReflection).filter(
            and_(
                SaturdayReflection.user_id == user_id,
                SaturdayReflection.reflection_date == reflection_date,
                SaturdayReflection.is_active == True
            )
        ).first()

    def create_or_update(
        self,
        *,
        user_id: int,
        reflection_date: date,
        segment_1: Optional[str] = None,
        segment_2: Optional[str] = None,
        segment_3: Optional[str] = None,
        segment_4: Optional[str] = None,
        segment_5: Optional[str] = None,
    ) -> SaturdayReflection:
        """Создать или обновить рефлексию пользователя."""
        existing = self.get_by_user_and_date(user_id, reflection_date)
        
        if existing:
            # Обновляем существующую рефлексию
            if segment_1 is not None:
                existing.segment_1 = segment_1
            if segment_2 is not None:
                existing.segment_2 = segment_2
            if segment_3 is not None:
                existing.segment_3 = segment_3
            if segment_4 is not None:
                existing.segment_4 = segment_4
            if segment_5 is not None:
                existing.segment_5 = segment_5
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Создаем новую рефлексию
            return self.create(
                user_id=user_id,
                reflection_date=reflection_date,
                segment_1=segment_1,
                segment_2=segment_2,
                segment_3=segment_3,
                segment_4=segment_4,
                segment_5=segment_5,
            )

