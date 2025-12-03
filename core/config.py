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
        protected_namespaces=('settings_',),
    )

    # Database
    database_url: Optional[str] = None
    postgres_host: str = ""
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""
    db_schema_name: str = "public"

    # Redis
    redis_url: Optional[str] = None
    redis_host: str = ""
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Telegram Bot
    bot_token: str = ""

    # Django
    secret_key: str = ""

    # Application
    app_name: str = "app"
    app_port: int = 8042
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
    
    # Feedback
    feedback_group_id: str | None = None

    # Cloud.ru API (Whisper)
    cloudru_iam_key: str = ""
    cloudru_iam_secret: str = ""
    whisper_model_url: str = ""
    whisper_model_name: str = ""

    # Cloud.ru API (Qwen)
    cloud_public_url: str = ""
    # Попробуем разные варианты моделей (если одна не работает, можно попробовать другую):
    # "library/qwen2.5:14b" - текстовая модель 14B параметров
    # "library/qwen2.5:7b" - текстовая модель 7B параметров (быстрее)
    # "library/qwen2.5vl:32b" - vision-language модель 32B (медленнее, но была рабочей)
    qwen_model: str = ""
    system_prompt: str = "Ты - полезный ассистент. Отвечай на русском языке."
    qwen_max_tokens: int = 512
    qwen_temperature: float = 0.2
    qwen_top_p: float = 0.9
    qwen_top_k: int = 10
    qwen_frequency_penalty: float = 0.0
    qwen_repetition_penalty: float = 1.03
    qwen_length_penalty: float = 1.0
    cloud_timeout: int = 300  # 5 минут - модель долго стартует (до 3 минут на первых запусках)
    cloud_iam_token_url: str = "https://auth.iam.sbercloud.ru/auth/system/openid/token"

    # AWS S3 (для Django admin panel)
    aws_s3_endpoint_url: str = ""
    aws_storage_bucket_name: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_querystring_auth: bool = True

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

