"""
Базовые настройки Django-проекта для административной панели.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.engine.url import make_url

from core.config import settings as core_settings


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-change-me"  # TODO: перенести в .env при необходимости

DEBUG = True  # Включаем для разработки, чтобы статика работала

ALLOWED_HOSTS: list[str] = ["*"]

INSTALLED_APPS = [
    "jazzmin",  # Современная тема для админки
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
    "payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "admin_panel.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "admin_panel.wsgi.application"


def _build_database_config() -> dict[str, Any]:
    """Преобразование SQLAlchemy database_url из core.settings в формат Django."""
    url = make_url(core_settings.db_url)
    engine_mapping = {
        "postgresql": "django.db.backends.postgresql",
        "postgresql+psycopg2": "django.db.backends.postgresql",
        "sqlite": "django.db.backends.sqlite3",
        "sqlite+pysqlite": "django.db.backends.sqlite3",
    }
    engine = engine_mapping.get(url.drivername)
    if engine is None:  # pragma: no cover - защитная ветка
        raise ValueError(f"Неподдерживаемый драйвер БД для Django: {url.drivername}")

    db_config = {
        "ENGINE": engine,
        "NAME": url.database or "",
        "USER": url.username or "",
        "PASSWORD": url.password or "",
        "HOST": url.host or "",
        "PORT": str(url.port or ""),
    }
    
    # Настройки подключения для PostgreSQL
    options = {}
    
    # Добавляем search_path только если схема указана и не пустая
    if core_settings.db_schema_name:
        options["options"] = f"-c search_path={core_settings.db_schema_name}"
    
    # Параметры подключения для стабильности
    if not options:
        options = {}
    
    # Параметры для psycopg2 через OPTIONS
    # connect_timeout - таймаут подключения в секундах
    # sslmode - режим SSL (disable, allow, prefer, require, verify-ca, verify-full)
    # Попробуем сначала без SSL, если не работает - изменим на require
    options["connect_timeout"] = "30"
    options["sslmode"] = "prefer"  # Пробуем с SSL, но не требуем его
    
    db_config["OPTIONS"] = options
    
    # Дополнительные параметры для подключения
    db_config["CONN_MAX_AGE"] = 0  # Не использовать постоянные соединения
    db_config["ATOMIC_REQUESTS"] = False
    
    # Таймаут подключения (в секундах) - передается напрямую в psycopg2
    # Это должно помочь с проблемой timeout expired
    
    return db_config


DATABASES = {
    "default": _build_database_config(),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Настройки Jazzmin (современная тема для админки)
JAZZMIN_SETTINGS = {
    "site_title": "Админ-панель бота рефлексии",
    "site_header": "Админ-панель бота рефлексии",
    "site_brand": "Бот рефлексии",
    "site_logo": None,
    "login_logo": None,
    "login_logo_dark": None,
    "site_logo_classes": "img-circle",
    "site_icon": None,
    "welcome_sign": "Добро пожаловать в админ-панель бота рефлексии",
    "copyright": "Бот рефлексии",
    "search_model": ["auth.User", "dashboard.TelegramUser"],
    "user_avatar": None,
    "topmenu_links": [
        {"name": "Главная", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Пользователи", "url": "admin:dashboard_telegramuser_changelist"},
    ],
    "usermenu_links": [
        {"name": "Изменить пароль", "url": "admin:password_change"},
        {"model": "auth.user"},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": ["auth", "dashboard"],
    "custom_links": {
        "dashboard": [{
            "name": "Статистика",
            "url": "admin:index",
            "icon": "fas fa-chart-line",
        }]
    },
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "dashboard.TelegramUser": "fas fa-user-tie",
        "dashboard.QuizResult": "fas fa-poll",
        "dashboard.CourseDay": "fas fa-calendar-day",
        "dashboard.TouchContent": "fas fa-video",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": None,
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-primary",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": False
}


