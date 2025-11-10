#!/usr/bin/env python
"""
Точка входа для управления Django-админкой.
"""
import os
import sys


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


