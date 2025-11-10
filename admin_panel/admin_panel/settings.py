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

DEBUG = core_settings.debug

ALLOWED_HOSTS: list[str] = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard",
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
    url = make_url(core_settings.database_url)
    engine_mapping = {
        "postgresql": "django.db.backends.postgresql",
        "postgresql+psycopg2": "django.db.backends.postgresql",
        "sqlite": "django.db.backends.sqlite3",
        "sqlite+pysqlite": "django.db.backends.sqlite3",
    }
    engine = engine_mapping.get(url.drivername)
    if engine is None:  # pragma: no cover - защитная ветка
        raise ValueError(f"Неподдерживаемый драйвер БД для Django: {url.drivername}")

    return {
        "ENGINE": engine,
        "NAME": url.database or "",
        "USER": url.username or "",
        "PASSWORD": url.password or "",
        "HOST": url.host or "",
        "PORT": str(url.port or ""),
        "OPTIONS": {
            "options": f"-c search_path={core_settings.db_schema_name}"
            if core_settings.db_schema_name
            else "",
        },
    }


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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


