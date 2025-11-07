from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from core.config import settings


engine = create_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=settings.debug,
    future=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    future=True
)


def get_session() -> Generator[Session, None, None]:
    """Генератор сессии для использования в зависимостях"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Алиас для get_session (совместимость)"""
    yield from get_session()


