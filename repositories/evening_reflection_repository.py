from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.repository import BaseRepository
from models.evening_reflection import EveningReflection


class EveningReflectionRepository(BaseRepository[EveningReflection]):
    """Репозиторий для вечерних рефлексий."""

    def __init__(self, session: Session):
        super().__init__(EveningReflection, session)

    def get_by_user_and_date(
        self,
        user_id: int,
        reflection_date: date
    ) -> Optional[EveningReflection]:
        """Получить рефлексию пользователя за конкретную дату."""
        return self.session.query(EveningReflection).filter(
            and_(
                EveningReflection.user_id == user_id,
                EveningReflection.reflection_date == reflection_date,
                EveningReflection.is_active == True
            )
        ).first()

    def create_or_update(
        self,
        *,
        user_id: int,
        reflection_date: date,
        reflection_text: str,
    ) -> EveningReflection:
        """Создать или обновить вечернюю рефлексию пользователя."""
        existing = self.get_by_user_and_date(user_id, reflection_date)
        
        if existing:
            # Обновляем существующую рефлексию
            existing.reflection_text = reflection_text
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Создаем новую рефлексию
            return self.create(
                user_id=user_id,
                reflection_date=reflection_date,
                reflection_text=reflection_text,
            )

