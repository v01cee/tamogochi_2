from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.repository import BaseRepository
from models.touch_answer import TouchAnswer


class TouchAnswerRepository(BaseRepository[TouchAnswer]):
    """Репозиторий для ответов на вопросы касаний."""

    def __init__(self, session: Session):
        super().__init__(TouchAnswer, session)

    def create_answers(
        self,
        *,
        user_id: int,
        touch_content_id: int,
        touch_date: date,
        answers: List[str],
    ) -> List[TouchAnswer]:
        """Создать ответы на все вопросы касания."""
        created_answers = []
        for index, answer_text in enumerate(answers):
            answer = self.create(
                user_id=user_id,
                touch_content_id=touch_content_id,
                touch_date=touch_date,
                question_index=index,
                answer_text=answer_text,
            )
            created_answers.append(answer)
        return created_answers

    def get_by_user_and_content_and_date(
        self,
        user_id: int,
        touch_content_id: int,
        touch_date: date
    ) -> List[TouchAnswer]:
        """Получить все ответы пользователя на конкретное касание за конкретную дату."""
        return list(
            self.session.query(TouchAnswer).filter(
                and_(
                    TouchAnswer.user_id == user_id,
                    TouchAnswer.touch_content_id == touch_content_id,
                    TouchAnswer.touch_date == touch_date,
                    TouchAnswer.is_active == True
                )
            ).order_by(TouchAnswer.question_index).all()
        )

