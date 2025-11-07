from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий с CRUD операциями"""

    def __init__(self, model: Type[ModelType], session: Session):
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Получить запись по ID"""
        return self.session.get(self.model, id)

    def get_all(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[ModelType]:
        """Получить все записи с пагинацией"""
        query = select(self.model)
        if active_only:
            query = query.where(self.model.is_active == True)
        query = query.offset(skip).limit(limit)
        return list(self.session.scalars(query).all())

    def create(self, **kwargs) -> ModelType:
        """Создать новую запись"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Обновить запись"""
        instance = self.get_by_id(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            self.session.commit()
            self.session.refresh(instance)
        return instance

    def delete(self, id: int, soft: bool = True) -> bool:
        """Удалить запись (soft delete по умолчанию)"""
        instance = self.get_by_id(id)
        if instance:
            if soft:
                instance.is_active = False
                self.session.commit()
            else:
                self.session.delete(instance)
                self.session.commit()
            return True
        return False

    def filter_by(self, **kwargs) -> List[ModelType]:
        """Фильтрация по параметрам"""
        query = select(self.model).filter_by(**kwargs)
        return list(self.session.scalars(query).all())


