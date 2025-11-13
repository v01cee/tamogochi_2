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
    postgres_host: str = "109.73.202.83"
    postgres_port: int = 5435
    postgres_user: str = "admin"
    postgres_password: str = "123b1h23b1kgasfbasfas123"
    postgres_db: str = "testing_postgres"
    db_schema_name: str = "public"

    # Redis
    redis_url: Optional[str] = None
    redis_host: str = "109.73.202.83"
    redis_port: int = 6700
    redis_password: Optional[str] = "An0th3rStr0ngR3disP@ss"
    redis_db: int = 0

    # Telegram Bot
    bot_token: str = "8571264937:AAEKtzODxcWczIL4RTdqGosdt2gsFROElPs"

    # Application
    app_name: str = "tamogochi_2"
    app_port: int = 8042
    debug: bool = False
    timezone: str = "Europe/Moscow"
    media_root: str = "media"

    # Robokassa
    robokassa_shop_id: str = "happinesscourse"
    robokassa_password1: str = "lpDr4hE1dSCuq8Ts34eH"
    robokassa_password2: str = "N7bN3Iqw4gsNZaVx2v5N"
    robokassa_is_test: bool = True
    robokassa_base_url: str = "https://auth.robokassa.ru/Merchant/Index.aspx"
    robokassa_success_url: str | None = "https://example.com/payments/success"
    robokassa_fail_url: str | None = "https://example.com/payments/fail"
    robokassa_result_secret: str | None = None

    # Community
    community_chat_url: str | None = None

    # Cloud.ru API (Whisper)
    cloudru_iam_key: str = "c58abbc2dec1a95792855148490e4f30"
    cloudru_iam_secret: str = "bcfc161c3f9ad95935b1f448e8ce6a91"
    whisper_model_url: str = "https://4b58beb9-6f1b-4f73-ba39-064e7f180db3.modelrun.inference.cloud.ru"
    whisper_model_name: str = "model-run-wxryh-soft"

    # Cloud.ru API (Qwen)
    cloud_public_url: str = "https://736bb669-5df9-42d5-8df6-1170ef1b9a4e.modelrun.inference.cloud.ru"
    # Попробуем разные варианты моделей (если одна не работает, можно попробовать другую):
    # "library/qwen2.5:14b" - текстовая модель 14B параметров
    # "library/qwen2.5:7b" - текстовая модель 7B параметров (быстрее)
    # "library/qwen2.5vl:32b" - vision-language модель 32B (медленнее, но была рабочей)
    qwen_model: str = "library/qwen2.5vl:32b"  # Возвращаем рабочую модель (дообучающаяся, долго стартует)
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

