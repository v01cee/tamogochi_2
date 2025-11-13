#!/usr/bin/env python
"""Применение миграций Django"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Меняем рабочую директорию на admin_panel для правильного импорта
os.chdir(BASE_DIR / "admin_panel")

# Устанавливаем переменную окружения для Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.settings")

# Импортируем Django
import django
django.setup()

# Применяем миграции
from django.core.management import call_command

if __name__ == "__main__":
    print("Применение миграций Django...")
    try:
        call_command('migrate', verbosity=1, interactive=False)
        print("\n✓ Миграции применены успешно!")
        print("\nТеперь можно создать суперпользователя:")
        print("  python admin_panel/manage.py createsuperuser")
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

