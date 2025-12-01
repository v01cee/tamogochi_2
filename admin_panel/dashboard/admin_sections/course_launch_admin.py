"""CourseLaunch admin configuration."""

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone

from ..models import CourseLaunch

logger = logging.getLogger(__name__)

ACTIVE_SUBSCRIPTION_TYPES = {"trial", "paid"}


@admin.register(CourseLaunch)
class CourseLaunchAdmin(admin.ModelAdmin):
    list_display = ("launch_date", "started_at", "started_by", "users_count", "is_active")
    list_filter = ("is_active", "started_at")
    readonly_fields = ("started_at", "started_by", "users_count", "created_at", "updated_at")
    fields = (
        "launch_date",
        "is_active",
        "started_at",
        "started_by",
        "users_count",
        "created_at",
        "updated_at",
    )
    actions = ["launch_course_process"]

    def has_add_permission(self, request):
        """Запрещаем ручное создание - только через action."""
        return False

    def launch_course_process(self, request, queryset):
        """Запустить процесс курса - установить дату старта для всех пользователей с подпиской."""
        from django.db import connection

        # Вычисляем следующий понедельник
        tz = ZoneInfo("Europe/Moscow")
        now = datetime.now(tz=tz)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:  # Если сегодня понедельник, берем следующий
            days_until_monday = 7
        next_monday = (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        try:
            with transaction.atomic():
                # Деактивируем все предыдущие запуски
                CourseLaunch.objects.filter(is_active=True).update(is_active=False)

                # Получаем количество пользователей с активной подпиской
                subscription_types_list = list(ACTIVE_SUBSCRIPTION_TYPES)
                placeholders = ",".join(["%s"] * len(subscription_types_list))
                
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT COUNT(*) 
                        FROM users 
                        WHERE subscription_type IN ({placeholders})
                        AND is_active = true
                        """,
                        subscription_types_list,
                    )
                    users_count = cursor.fetchone()[0]

                # Создаем новую запись о запуске
                launch = CourseLaunch.objects.create(
                    launch_date=next_monday,
                    started_by=request.user.username or str(request.user),
                    users_count=users_count,
                    is_active=True,
                )

                # Обновляем subscription_started_at для всех пользователей с подпиской
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        UPDATE users 
                        SET subscription_started_at = %s,
                            morning_touch_sent_at = NULL,
                            day_touch_sent_at = NULL,
                            evening_touch_sent_at = NULL
                        WHERE subscription_type IN ({placeholders})
                        AND is_active = true
                        """,
                        [next_monday] + subscription_types_list,
                    )
                    updated_count = cursor.rowcount

                self.message_user(
                    request,
                    f"✓ Процесс курса запущен!\n"
                    f"📅 Стартовая дата: {next_monday.strftime('%d.%m.%Y %H:%M')}\n"
                    f"👥 Обновлено пользователей: {updated_count}\n"
                    f"📧 Рассылка касаний начнется с {next_monday.strftime('%d.%m.%Y')} (понедельник)",
                    messages.SUCCESS,
                )

                logger.info(
                    f"[COURSE_LAUNCH] Процесс запущен: старт {next_monday}, пользователей {updated_count}"
                )

        except Exception as exc:
            logger.error(f"[COURSE_LAUNCH] Ошибка при запуске процесса: {exc}", exc_info=True)
            self.message_user(
                request,
                f"❌ Ошибка при запуске процесса: {str(exc)}",
                messages.ERROR,
            )

    launch_course_process.short_description = "🚀 Запустить процесс курса (следующий понедельник)"

