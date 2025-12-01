from django.contrib import admin

from ..models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Раздел 'Обратная связь' в админке."""

    list_display = ("created_at", "telegram_id", "username", "full_name", "short_text", "is_active")
    list_filter = ("is_active",)
    search_fields = ("telegram_id", "username", "full_name", "message_text")
    readonly_fields = ("telegram_id", "username", "full_name", "message_text", "created_at", "updated_at", "is_active")
    ordering = ("-created_at",)

    def short_text(self, obj: Feedback) -> str:  # type: ignore[override]
        text = obj.message_text or ""
        return text[:80] + ("..." if len(text) > 80 else "")

    short_text.short_description = "Текст"


