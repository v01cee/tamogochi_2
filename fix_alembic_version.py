"""Скрипт для исправления версии Alembic в базе данных."""

import sys
from sqlalchemy import create_engine, text

# Захардкоженная строка подключения к PostgreSQL
DB_URL = "postgresql://admin:123b1h23b1kgasfbasfas123@109.73.202.83:5435/testing_postgres"

def fix_alembic_version():
    """Исправить версию Alembic в базе данных."""
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        # Проверяем текущую версию
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_version = result.scalar()
        
        print(f"Текущая версия в БД: {current_version}")
        
        # Проверяем, какие таблицы уже существуют
        tables_check = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('touch_answers', 'evening_reflections', 'evening_ratings', 'saturday_reflections')
        """))
        existing_tables = [row[0] for row in tables_check]
        
        print(f"Существующие таблицы: {existing_tables}")
        
        # Проверяем, есть ли таблица users с полями day_touch_sent_at и evening_touch_sent_at
        columns_check = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'users' 
            AND column_name IN ('day_touch_sent_at', 'evening_touch_sent_at')
        """))
        existing_columns = [row[0] for row in columns_check]
        
        print(f"Существующие колонки в users: {existing_columns}")
        
        # Определяем правильную версию
        if 'day_touch_sent_at' in existing_columns and 'evening_touch_sent_at' in existing_columns:
            # Миграция 0002 применена
            if len(existing_tables) == 0:
                # Нужно применить миграцию 0003
                target_version = "0002"
                print(f"Миграция 0002 применена. Устанавливаем версию: {target_version}")
            else:
                # Все миграции применены
                target_version = "0003"
                print(f"Все миграции применены. Устанавливаем версию: {target_version}")
        else:
            # Только миграция 0001 применена
            target_version = "0001_initial"
            print(f"Только миграция 0001 применена. Устанавливаем версию: {target_version}")
        
        # Обновляем версию
        if current_version != target_version:
            conn.execute(text(f"UPDATE alembic_version SET version_num = '{target_version}'"))
            conn.commit()
            print(f"✓ Версия обновлена с '{current_version}' на '{target_version}'")
        else:
            print(f"✓ Версия уже правильная: {target_version}")
        
        # Проверяем результат
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        new_version = result.scalar()
        print(f"Новая версия в БД: {new_version}")

if __name__ == "__main__":
    try:
        fix_alembic_version()
        print("\n✓ Готово! Теперь можно запустить: alembic upgrade head")
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

