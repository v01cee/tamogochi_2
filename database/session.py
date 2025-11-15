from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from core.config import settings


connect_args = {}
if not settings.db_url.startswith("sqlite"):
    connect_args = {
        "connect_timeout": 10,  # Таймаут подключения 10 секунд
        "options": "-c statement_timeout=30000",  # Таймаут запросов 30 секунд
    }

engine = create_engine(
    settings.db_url,
    poolclass=NullPool,
    echo=settings.debug,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,  # Проверка соединения перед использованием
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


