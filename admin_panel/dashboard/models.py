from django.db import models


class TelegramUser(models.Model):
    """Django-модель для работы с таблицей пользователей Telegram."""

    telegram_id = models.BigIntegerField("Telegram ID", unique=True, db_index=True)
    username = models.CharField("Никнейм", max_length=255, blank=True, null=True)
    first_name = models.CharField("Имя", max_length=255, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=255, blank=True, null=True)
    language_code = models.CharField("Язык", max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"

    def __str__(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or str(self.telegram_id)


