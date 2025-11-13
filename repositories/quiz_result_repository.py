from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import update

from database.repository import BaseRepository
from models.quiz_result import QuizResult


class QuizResultRepository(BaseRepository[QuizResult]):
    """Репозиторий для результатов стартового опроса."""

    def __init__(self, session: Session):
        super().__init__(QuizResult, session)

    def create_from_answers(
        self,
        *,
        user_id: int,
        answers: Sequence[int],
    ) -> QuizResult:
        if len(answers) != 6:
            raise ValueError("Ожидается шесть значений для радарной диаграммы.")

        energy, happiness, sleep, relationships, balance, strategy = answers

        # Деактивируем все предыдущие результаты этого пользователя
        # чтобы сохранялся только последний (финальный) вариант
        stmt = (
            update(QuizResult)
            .where(QuizResult.user_id == user_id)
            .where(QuizResult.is_active == True)
            .values(is_active=False)
        )
        self.session.execute(stmt)

        # Создаем новый результат (он будет активным по умолчанию)
        return self.create(
            user_id=user_id,
            energy=energy,
            happiness=happiness,
            sleep_quality=sleep,
            relationships_quality=relationships,
            life_balance=balance,
            strategy_level=strategy,
        )



