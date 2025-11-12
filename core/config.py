from __future__ import annotations

from typing import Optional
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: Optional[str] = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "tamogochi_db"
    db_schema_name: str = "public"

    # Redis
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Telegram Bot
    bot_token: str

    # Application
    app_name: str = "tamogochi_2"
    app_port: int = 8000
    debug: bool = False
    timezone: str = "Europe/Moscow"
    media_root: str = "media"

    # Robokassa
    robokassa_shop_id: str = ""
    robokassa_password1: str = ""
    robokassa_password2: str = ""
    robokassa_is_test: bool = True
    robokassa_base_url: str = "https://auth.robokassa.ru/Merchant/Index.aspx"
    robokassa_success_url: str | None = None
    robokassa_fail_url: str | None = None
    robokassa_result_secret: str | None = None

    # Community
    community_chat_url: str | None = None

    # Python
    python_version: str = "3.12"

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        user = quote_plus(self.postgres_user)
        password = f":{quote_plus(self.postgres_password)}" if self.postgres_password else ""
        return (
            f"postgresql://{user}{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_dsn(self) -> str:
        if self.redis_url:
            return self.redis_url
        password = f":{quote_plus(self.redis_password)}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()

