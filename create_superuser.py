#!/usr/bin/env python
"""Создание суперпользователя Django неинтерактивно"""
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

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Параметры суперпользователя
USERNAME = "v01ce"
EMAIL = "maksimagrig2@gmail.com"
PASSWORD = "v01ce"  # ИЗМЕНИ ЭТОТ ПАРОЛЬ!

if __name__ == "__main__":
    if User.objects.filter(username=USERNAME).exists():
        print(f"Пользователь '{USERNAME}' уже существует!")
        sys.exit(1)
    
    try:
        User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD
        )
        print(f"✓ Суперпользователь '{USERNAME}' успешно создан!")
        print(f"  Email: {EMAIL}")
        print(f"  Password: {PASSWORD}")
        print("\n⚠️  ВАЖНО: Измени пароль после первого входа!")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

