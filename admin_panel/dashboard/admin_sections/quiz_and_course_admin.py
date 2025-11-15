"""QuizResult and CourseDay admin configuration."""

from django.contrib import admin

from ..models import CourseDay, QuizResult, TouchContent


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "energy",
        "happiness",
        "sleep_quality",
        "relationships_quality",
        "life_balance",
        "strategy_level",
        "created_at",
        "is_active",
    )
    list_filter = ("created_at", "is_active")
    search_fields = (
        "user__telegram_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__full_name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "user",
        "energy",
        "happiness",
        "sleep_quality",
        "relationships_quality",
        "life_balance",
        "strategy_level",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_select_related = ("user",)

    def get_queryset(self, request):
        """По умолчанию показываем только активные результаты (последние финальные)"""
        qs = super().get_queryset(request)
        if "is_active__exact" not in request.GET:
            qs = qs.filter(is_active=True)
        return qs

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TouchContentInline(admin.StackedInline):
    model = TouchContent
    extra = 0
    fields = (
        "touch_type",
        "title",
        "is_active",
        "video_file",
        "video_url",
        "transcript",
        "questions",
    )


@admin.register(CourseDay)
class CourseDayAdmin(admin.ModelAdmin):
    list_display = ("day_number", "title", "is_active", "updated_at")
    list_editable = ("title", "is_active")
    ordering = ("day_number",)
    search_fields = ("title", "day_number")
    readonly_fields = ("day_number", "created_at", "updated_at")
    fields = ("day_number", "title", "is_active", "created_at", "updated_at")
    inlines = (TouchContentInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

