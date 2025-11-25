"""
Базовые настройки Django-проекта для административной панели.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.engine.url import make_url

# from core.config import settings as core_settings


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-temporary-key-for-debugging-only"  # Временный ключ для отладки

DEBUG = True  # Включаем DEBUG для просмотра деталей ошибок

ALLOWED_HOSTS: list[str] = ["*"]

INSTALLED_APPS = [
    "jazzmin",  # Современная тема для админки
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "storages",
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


# Импортируем настройки из core.config
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from core.config import settings as core_settings
    
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": core_settings.postgres_db or os.getenv("POSTGRES_DB", "testing_postgres"),
            "USER": core_settings.postgres_user or os.getenv("POSTGRES_USER", "admin"),
            "PASSWORD": core_settings.postgres_password or os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": core_settings.postgres_host or os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": core_settings.postgres_port or int(os.getenv("POSTGRES_PORT", "5432")),
            "OPTIONS": {
                "options": "-c statement_timeout=30000",
            },
        },
    }
except ImportError:
    # Fallback на переменные окружения напрямую, если core.config недоступен
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "testing_postgres"),
            "USER": os.getenv("POSTGRES_USER", "admin"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": int(os.getenv("POSTGRES_PORT", "5432")),
            "OPTIONS": {
                "options": "-c statement_timeout=30000",
            },
        },
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


AWS_S3_ENDPOINT_URL = ""  # core_settings.aws_s3_endpoint_url
AWS_STORAGE_BUCKET_NAME = ""  # core_settings.aws_storage_bucket_name
AWS_ACCESS_KEY_ID = ""  # core_settings.aws_access_key_id
AWS_SECRET_ACCESS_KEY = ""  # core_settings.aws_secret_access_key
AWS_QUERYSTRING_AUTH = True  # core_settings.aws_querystring_auth

# Используем S3 только если настроен bucket_name, иначе локальное хранилище
if AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = "admin_panel.dashboard.storage.MediaStorage"
    STATICFILES_STORAGE = "admin_panel.dashboard.storage.StaticStorage"
else:
    # Локальное хранилище по умолчанию
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

