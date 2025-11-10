from django.contrib import admin

from .models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_name", "language_code")
    search_fields = ("telegram_id", "username", "first_name", "last_name")
    list_filter = ("language_code",)
    ordering = ("-telegram_id",)
    readonly_fields = ("telegram_id", "username", "first_name", "last_name", "language_code")


