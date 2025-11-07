from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.user import User
from database.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Репозиторий для работы с пользователями"""

    def __init__(self, session: Session):
        super().__init__(User, session)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        query = select(User).where(User.telegram_id == telegram_id)
        return self.session.scalar(query)

    def get_or_create(self, telegram_id: int, **kwargs) -> User:
        """Получить или создать пользователя"""
        user = self.get_by_telegram_id(telegram_id)
        if not user:
            user = self.create(telegram_id=telegram_id, **kwargs)
        return user


