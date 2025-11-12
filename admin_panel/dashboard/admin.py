from django.contrib import admin

from .models import CourseDay, QuizResult, TelegramUser, TouchContent


class QuizResultInline(admin.TabularInline):
    model = QuizResult
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "created_at",
        "energy",
        "happiness",
        "sleep_quality",
        "relationships_quality",
        "life_balance",
        "strategy_level",
        "is_active",
    )
    ordering = ("-created_at",)
    show_change_link = True


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "subscription_type",
        "subscription_started_at",
        "consent_accepted_at",
        "full_name",
        "role",
        "company",
        "latest_quiz_result",
        "created_at",
    )
    search_fields = (
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "full_name",
        "role",
        "company",
    )
    list_filter = (
        "subscription_type",
        "language_code",
        "is_active",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "telegram_id",
        "username",
        "first_name",
        "last_name",
        "language_code",
        "full_name",
        "role",
        "company",
        "subscription_type",
        "subscription_started_at",
        "subscription_paid_at",
        "consent_accepted_at",
        "created_at",
        "updated_at",
        "is_active",
    )
    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "telegram_id",
                    "username",
                    "first_name",
                    "last_name",
                    "language_code",
                    "is_active",
                )
            },
        ),
        (
            "Профиль",
            {
                "fields": (
                    "full_name",
                    "role",
                    "company",
                )
            },
        ),
        (
            "Подписка",
            {
                "fields": (
                    "subscription_type",
                    "subscription_started_at",
                    "subscription_paid_at",
                )
            },
        ),
        (
            "Согласия и таймстемпы",
            {
                "fields": (
                    "consent_accepted_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    inlines = (QuizResultInline,)

    def latest_quiz_result(self, obj):
        result = obj.quiz_results.order_by("-created_at").first()
        if not result:
            return "—"
        return (
            f"Э:{result.energy} Сч:{result.happiness} Сон:{result.sleep_quality} "
            f"Отн:{result.relationships_quality} Бал:{result.life_balance} Стр:{result.strategy_level}"
        )

    latest_quiz_result.short_description = "Стартовый портрет"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TouchContentInline(admin.StackedInline):
    model = TouchContent
    extra = 0
    fields = (
        "touch_type",
        "step_code",
        "title",
        "is_active",
        "order_index",
        "video_file",
        "video_url",
        "summary",
        "transcript",
        "questions",
    )


@admin.register(CourseDay)
class CourseDayAdmin(admin.ModelAdmin):
    list_display = ("day_number", "title", "is_active", "updated_at")
    list_editable = ("title", "is_active")
    ordering = ("day_number",)
    search_fields = ("title",)
    readonly_fields = ("day_number", "created_at", "updated_at")
    fields = ("day_number", "title", "is_active", "created_at", "updated_at")
    inlines = (TouchContentInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TouchContent)
class TouchContentAdmin(admin.ModelAdmin):
    list_display = (
        "course_day",
        "title",
        "touch_type",
        "step_code",
        "is_active",
        "order_index",
        "updated_at",
    )
    list_filter = ("touch_type", "is_active", "course_day")
    search_fields = ("title", "step_code", "summary", "questions")
    ordering = ("course_day__day_number", "touch_type", "order_index", "-updated_at")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Общее",
            {
                "fields": (
                    "course_day",
                    "touch_type",
                    "step_code",
                    "title",
                    "is_active",
                    "order_index",
                )
            },
        ),
        (
            "Контент",
            {
                "fields": (
                    "video_file",
                    "video_url",
                    "summary",
                    "transcript",
                    "questions",
                )
            },
        ),
        (
            "Служебное",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
