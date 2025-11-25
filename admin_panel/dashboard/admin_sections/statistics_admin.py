"""Admin configuration for statistics and user answers."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, timedelta

from ..models import (
    TouchAnswer,
    EveningReflection,
    EveningRating,
    SaturdayReflection,
    TouchContent,
    TelegramUser,
)


@admin.register(TouchAnswer)
class TouchAnswerAdmin(admin.ModelAdmin):
    """Админ-класс для ответов на касания (скрыт из меню, используется только в inline)."""
    
    def has_module_permission(self, request):
        """Скрыть из меню админки."""
        return False
    list_display = (
        "user",
        "touch_content_display",
        "touch_date",
        "question_index_display",
        "answer_preview",
        "created_at",
    )
    list_filter = (
        "touch_date",
        "touch_content__touch_type",
        "created_at",
        "is_active",
    )
    search_fields = (
        "user__telegram_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__full_name",
        "answer_text",
    )
    ordering = ("-touch_date", "-created_at", "question_index")
    readonly_fields = (
        "user",
        "touch_content",
        "touch_date",
        "question_index",
        "answer_text",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_select_related = ("user", "touch_content")
    date_hierarchy = "touch_date"

    def touch_content_display(self, obj):
        return f"{obj.touch_content.get_touch_type_display()} - {obj.touch_content.title[:50]}"
    touch_content_display.short_description = "Тип касания"

    def question_index_display(self, obj):
        return f"Вопрос {obj.question_index + 1}"
    question_index_display.short_description = "Вопрос"

    def answer_preview(self, obj):
        preview = obj.answer_text[:100] + "..." if len(obj.answer_text) > 100 else obj.answer_text
        return format_html('<span title="{}">{}</span>', obj.answer_text, preview)
    answer_preview.short_description = "Ответ"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EveningReflection)
class EveningReflectionAdmin(admin.ModelAdmin):
    """Админ-класс для вечерних рефлексий (скрыт из меню, используется только в inline)."""
    
    def has_module_permission(self, request):
        """Скрыть из меню админки."""
        return False
    list_display = (
        "user",
        "reflection_date",
        "reflection_preview",
        "created_at",
    )
    list_filter = (
        "reflection_date",
        "created_at",
        "is_active",
    )
    search_fields = (
        "user__telegram_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__full_name",
        "reflection_text",
    )
    ordering = ("-reflection_date", "-created_at")
    readonly_fields = (
        "user",
        "reflection_date",
        "reflection_text",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_select_related = ("user",)
    date_hierarchy = "reflection_date"

    def reflection_preview(self, obj):
        preview = obj.reflection_text[:150] + "..." if len(obj.reflection_text) > 150 else obj.reflection_text
        return format_html('<span title="{}">{}</span>', obj.reflection_text, preview)
    reflection_preview.short_description = "Рефлексия"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EveningRating)
class EveningRatingAdmin(admin.ModelAdmin):
    """Админ-класс для вечерних оценок (скрыт из меню, используется только в inline)."""
    
    def has_module_permission(self, request):
        """Скрыть из меню админки."""
        return False
    list_display = (
        "user",
        "rating_date",
        "rating_energy",
        "rating_happiness",
        "rating_progress",
        "average_rating",
        "created_at",
    )
    list_filter = (
        "rating_date",
        "created_at",
        "is_active",
    )
    search_fields = (
        "user__telegram_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__full_name",
    )
    ordering = ("-rating_date", "-created_at")
    readonly_fields = (
        "user",
        "rating_date",
        "rating_energy",
        "rating_happiness",
        "rating_progress",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_select_related = ("user",)
    date_hierarchy = "rating_date"

    def average_rating(self, obj):
        avg = (obj.rating_energy + obj.rating_happiness + obj.rating_progress) / 3
        return f"{avg:.1f}"
    average_rating.short_description = "Средняя оценка"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaturdayReflection)
class SaturdayReflectionAdmin(admin.ModelAdmin):
    """Админ-класс для рефлексий стратсубботы (скрыт из меню, используется только в inline)."""
    
    def has_module_permission(self, request):
        """Скрыть из меню админки."""
        return False
    list_display = (
        "user",
        "reflection_date",
        "segments_completed",
        "created_at",
    )
    list_filter = (
        "reflection_date",
        "created_at",
        "is_active",
    )
    search_fields = (
        "user__telegram_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__full_name",
        "segment_1",
        "segment_2",
        "segment_3",
        "segment_4",
        "segment_5",
    )
    ordering = ("-reflection_date", "-created_at")
    readonly_fields = (
        "user",
        "reflection_date",
        "segment_1",
        "segment_2",
        "segment_3",
        "segment_4",
        "segment_5",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_select_related = ("user",)
    date_hierarchy = "reflection_date"
    fieldsets = (
        ("Основная информация", {
            "fields": ("user", "reflection_date", "is_active")
        }),
        ("Сегменты рефлексии", {
            "fields": (
                "segment_1",
                "segment_2",
                "segment_3",
                "segment_4",
                "segment_5",
            )
        }),
        ("Таймстемпы", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

