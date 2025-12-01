from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from ..models import BotSettings


@admin.register(BotSettings)
class BotSettingsAdmin(admin.ModelAdmin):
    """Раздел 'Обратная связь' в админке - настройки для пересылки сообщений в группу."""

    def get_object(self, request, object_id=None, from_field=None):
        """Автоматически создаем запись, если её нет."""
        obj = super().get_object(request, object_id, from_field)
        if obj is None:
            # Создаем запись с pk=1, если её нет
            obj, created = BotSettings.objects.get_or_create(pk=1)
        return obj

    fieldsets = (
        (
            "Настройки обратной связи",
            {
                "fields": ("feedback_group_id",),
                "description": "Укажите ID группы/канала в Telegram, куда будут пересылаться сообщения обратной связи от пользователей. ID может быть отрицательным числом (например, -5034565380). Получить ID можно командой /get_group_id в группе или через бота @userinfobot/@getidsbot.",
            },
        ),
        (
            "Администраторы бота",
            {
                "fields": ("telegram_admin_ids",),
                "description": "ID администраторов Telegram через запятую (например: 123456789,987654321). Получить свой ID можно через бота @userinfobot.",
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
        """Разрешаем создание записи, если её еще нет (только одна запись)."""
        # Проверяем, существует ли уже запись с pk=1
        if BotSettings.objects.filter(pk=1).exists():
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление - настройки должны существовать."""
        return False
    
    def changelist_view(self, request, extra_context=None):
        """Автоматически создаем запись при открытии списка и перенаправляем на редактирование."""
        # Создаем запись, если её нет
        obj, created = BotSettings.objects.get_or_create(pk=1)
        # Перенаправляем на страницу редактирования
        return redirect(reverse('admin:dashboard_botsettings_change', args=[obj.pk]))


