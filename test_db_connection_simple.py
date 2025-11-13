"""Простая проверка подключения к PostgreSQL"""
import sys
from sqlalchemy import create_engine, text
from core.config import settings

print(f"Попытка подключения к БД: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
print(f"Пользователь: {settings.postgres_user}")

try:
    engine = create_engine(
        settings.db_url,
        connect_args={"connect_timeout": 10}
    )
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        version = result.fetchone()[0]
        print(f"\n✓ Подключение успешно!")
        print(f"PostgreSQL версия: {version[:80]}...")
        
        # Проверяем состояние БД
        result = conn.execute(text("SELECT pg_is_in_recovery();"))
        is_recovering = result.fetchone()[0]
        
        if is_recovering:
            print("\n⚠ ВНИМАНИЕ: База данных находится в режиме восстановления (recovery mode)")
            print("   Это означает, что БД восстанавливается после перезапуска или сбоя.")
            print("   Подождите несколько минут и попробуйте снова.")
        else:
            print("\n✓ База данных готова к работе")
            
        # Проверяем доступные таблицы
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """))
        tables = result.fetchall()
        print(f"\nНайдено таблиц в схеме public: {len(tables)}")
        if tables:
            print("Первые 10 таблиц:")
            for table in tables[:10]:
                print(f"  - {table[0]}")
        
except Exception as e:
    print(f"\n✗ Ошибка подключения: {e}")
    print("\nВозможные причины:")
    print("1. База данных находится в процессе восстановления")
    print("2. Сервер PostgreSQL недоступен")
    print("3. Неверные учетные данные")
    print("4. Проблемы с сетью")
    sys.exit(1)

