from django.contrib import admin

from ..models import BotSettings


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """Раздел 'Обратная связь' в админке - настройки для пересылки сообщений в группу."""

    fieldsets = (
        (
            "Настройки обратной связи",
            {
                "fields": ("feedback_group_id",),
                "description": "Укажите ID группы/канала в Telegram, куда будут пересылаться сообщения обратной связи от пользователей. ID может быть отрицательным числом (например, -5034565380). Получить ID можно командой /get_group_id в группе или через бота @userinfobot/@getidsbot.",
            },
        ),
        (
            "Служебное",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
    readonly_fields = ("created_at", "updated_at")
    
    def has_add_permission(self, request):
        """Запрещаем создание новых записей - только одна запись."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление - настройки должны существовать."""
        return False


