#!/usr/bin/env python
"""
Точка входа для управления Django-админкой.
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main() -> None:
    """Запуск административных команд Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - защитный код
        raise ImportError(
            "Не удалось импортировать Django. Убедитесь, что пакет установлен "
            "и доступен в текущей среде."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()


