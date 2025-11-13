#!/usr/bin/env python
"""Проверка подключения к БД и применения миграций Django"""
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.settings")

import django
django.setup()

from django.db import connection
from django.core.management import call_command

print("Проверка подключения к БД...")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✓ Подключение успешно. PostgreSQL версия: {version[0][:50]}")
        
        # Проверяем существующие таблицы
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\nСуществующие таблицы в схеме public ({len(tables)}):")
        for table in tables[:20]:  # Показываем первые 20
            print(f"  - {table[0]}")
        if len(tables) > 20:
            print(f"  ... и еще {len(tables) - 20} таблиц")
        
        # Проверяем наличие auth_user
        has_auth_user = any(t[0] == 'auth_user' for t in tables)
        if has_auth_user:
            print("\n✓ Таблица auth_user существует")
        else:
            print("\n✗ Таблица auth_user НЕ существует - нужно применить миграции")
            
except Exception as e:
    print(f"✗ Ошибка подключения: {e}")
    sys.exit(1)

print("\nПрименение миграций Django...")
try:
    call_command('migrate', verbosity=2, interactive=False)
    print("✓ Миграции применены успешно")
except Exception as e:
    print(f"✗ Ошибка при применении миграций: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

