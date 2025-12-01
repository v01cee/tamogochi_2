"""Утилиты для работы с администраторами бота из БД."""

import os
import sys
from pathlib import Path
from typing import List

# Флаг для отслеживания инициализации Django
_django_setup_done = False


def ensure_django_setup():
    """Настраивает Django перед импортом моделей."""
    global _django_setup_done
    
    if _django_setup_done:
        # Проверяем, что Django действительно настроен
        try:
            import django
            if hasattr(django, 'apps') and hasattr(django.apps, 'apps'):
                if django.apps.apps.ready:
                    return  # Django настроен
        except (AttributeError, RuntimeError):
            pass  # Проверим снова
    
    # Добавляем пути в sys.path для Django
    project_root = Path(__file__).parent.parent.resolve()
    admin_panel_dir = project_root / "admin_panel"
    
    # Добавляем корневую директорию проекта (чтобы найти admin_panel)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Добавляем директорию admin_panel (чтобы Django мог найти приложения dashboard, payments)
    if str(admin_panel_dir) not in sys.path:
        sys.path.insert(0, str(admin_panel_dir))
    
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_panel.admin_panel.settings")
    
    import django
    
    # Настраиваем Django
    try:
        django.setup()
        _django_setup_done = True
    except RuntimeError:
        # Django может выбросить RuntimeError если уже настроен
        # Проверяем, действительно ли настроен
        try:
            if hasattr(django, 'apps') and hasattr(django.apps, 'apps'):
                if django.apps.apps.ready:
                    _django_setup_done = True
                    return
        except (AttributeError, RuntimeError):
            pass
        # Если не настроен, пробрасываем ошибку
        raise


def get_admin_ids() -> List[int]:
    """
    Получить список ID администраторов из БД.
    
    Returns:
        Список ID администраторов (может быть пустым).
    """
    try:
        ensure_django_setup()
        from admin_panel.dashboard.models import BotSettings
        
        # Синхронный вызов для получения настроек
        settings = BotSettings.get_settings()
        admin_ids_str = settings.telegram_admin_ids
        
        if not admin_ids_str or not admin_ids_str.strip():
            return []
        
        # Парсим строку вида "123,456,789" или "123 456 789"
        ids = []
        for part in admin_ids_str.replace(",", " ").split():
            part = part.strip()
            if part:
                try:
                    ids.append(int(part))
                except ValueError:
                    continue
        
        return ids
    except Exception:
        # Если ошибка при получении из БД, возвращаем пустой список
        return []


async def get_admin_ids_async() -> List[int]:
    """
    Асинхронная версия получения списка ID администраторов из БД.
    
    Returns:
        Список ID администраторов (может быть пустым).
    """
    try:
        ensure_django_setup()
        from asgiref.sync import sync_to_async
        from admin_panel.dashboard.models import BotSettings
        
        # Асинхронный вызов для получения настроек
        get_settings = sync_to_async(BotSettings.get_settings)
        settings = await get_settings()
        admin_ids_str = settings.telegram_admin_ids
        
        if not admin_ids_str or not admin_ids_str.strip():
            return []
        
        # Парсим строку вида "123,456,789" или "123 456 789"
        ids = []
        for part in admin_ids_str.replace(",", " ").split():
            part = part.strip()
            if part:
                try:
                    ids.append(int(part))
                except ValueError:
                    continue
        
        return ids
    except Exception:
        # Если ошибка при получении из БД, возвращаем пустой список
        return []


def is_admin(telegram_id: int) -> bool:
    """
    Проверить, является ли пользователь администратором.
    
    Args:
        telegram_id: Telegram ID пользователя.
        
    Returns:
        True, если пользователь является администратором.
    """
    admin_ids = get_admin_ids()
    return telegram_id in admin_ids


async def is_admin_async(telegram_id: int) -> bool:
    """
    Асинхронная версия проверки, является ли пользователь администратором.
    
    Args:
        telegram_id: Telegram ID пользователя.
        
    Returns:
        True, если пользователь является администратором.
    """
    admin_ids = await get_admin_ids_async()
    return telegram_id in admin_ids

