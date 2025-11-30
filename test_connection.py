"""Тестовый скрипт для проверки подключений и конфигурации"""
import asyncio
import sys
from core.config import settings
from database.session import SessionLocal

def test_config():
    """Проверка конфигурации"""
    print("=== Проверка конфигурации ===")
    print(f"PostgreSQL Host: {settings.postgres_host}")
    print(f"PostgreSQL Port: {settings.postgres_port}")
    print(f"PostgreSQL User: {settings.postgres_user}")
    print(f"PostgreSQL DB: {settings.postgres_db}")
    print(f"Redis Host: {settings.redis_host}")
    print(f"Redis Port: {settings.redis_port}")
    print(f"Bot Token: {'*' * 10 if settings.bot_token else 'НЕ УСТАНОВЛЕН'}")
    print(f"Admin IDs: {settings.telegram_admin_ids}")
    print()

def test_db_connection():
    """Проверка подключения к БД"""
    print("=== Проверка подключения к БД ===")
    try:
        db = SessionLocal()
        result = db.execute("SELECT 1")
        print("✅ Подключение к PostgreSQL успешно!")
        db.close()
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False
    return True

def test_redis_connection():
    """Проверка подключения к Redis"""
    print("=== Проверка подключения к Redis ===")
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        print("✅ Подключение к Redis успешно!")
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False
    return True

def test_imports():
    """Проверка импортов"""
    print("=== Проверка импортов ===")
    try:
        import limited_aiogram
        print("✅ limited_aiogram импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта limited_aiogram: {e}")
        return False
    
    try:
        from aiogram import Bot, Dispatcher
        print("✅ aiogram импортирован")
    except Exception as e:
        print(f"❌ Ошибка импорта aiogram: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 Начинаем проверку...\n")
    
    test_config()
    
    if not test_imports():
        sys.exit(1)
    
    if not test_db_connection():
        sys.exit(1)
    
    if not test_redis_connection():
        sys.exit(1)
    
    print("\n✅ Все проверки пройдены! Можно запускать бота.")



