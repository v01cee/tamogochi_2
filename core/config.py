from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    database_url: str
    db_schema_name: str = "public"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Telegram Bot
    bot_token: str

    # Application
    app_name: str = "tamogochi_2"
    app_port: int = 8000
    debug: bool = False

    # Python
    python_version: str = "3.12"


settings = Settings()


