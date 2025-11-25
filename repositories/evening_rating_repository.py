from datetime import date
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.repository import BaseRepository
from models.evening_rating import EveningRating


class EveningRatingRepository(BaseRepository[EveningRating]):
    """Репозиторий для вечерних оценок."""

    def __init__(self, session: Session):
        super().__init__(EveningRating, session)

    def get_by_user_and_date(
        self,
        user_id: int,
        rating_date: date
    ) -> Optional[EveningRating]:
        """Получить оценки пользователя за конкретную дату."""
        return self.session.query(EveningRating).filter(
            and_(
                EveningRating.user_id == user_id,
                EveningRating.rating_date == rating_date,
                EveningRating.is_active == True
            )
        ).first()

    def create_or_update(
        self,
        *,
        user_id: int,
        rating_date: date,
        rating_energy: int,
        rating_happiness: int,
        rating_progress: int,
    ) -> EveningRating:
        """Создать или обновить вечерние оценки пользователя."""
        existing = self.get_by_user_and_date(user_id, rating_date)
        
        if existing:
            # Обновляем существующие оценки
            existing.rating_energy = rating_energy
            existing.rating_happiness = rating_happiness
            existing.rating_progress = rating_progress
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            # Создаем новые оценки
            return self.create(
                user_id=user_id,
                rating_date=rating_date,
                rating_energy=rating_energy,
                rating_happiness=rating_happiness,
                rating_progress=rating_progress,
            )

