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
        else:
            updated = False
            for field, value in kwargs.items():
                if value is not None and hasattr(user, field) and getattr(user, field) != value:
                    setattr(user, field, value)
                    updated = True
            if updated:
                self.session.commit()
                self.session.refresh(user)
        return user

    def set_notification_time(self, user: User, touch_type: str, value) -> User:
        field_map = {
            "morning": "morning_notification_time",
            "day": "day_notification_time",
            "evening": "evening_notification_time",
        }
        field = field_map.get(touch_type)
        if not field:
            raise ValueError(f"Unknown touch type: {touch_type}")
        setattr(user, field, value)
        self.session.commit()
        self.session.refresh(user)
        return user


