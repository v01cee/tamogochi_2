"""TelegramUser admin configuration and related actions."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.contrib import admin, messages

from core.config import settings
from ..models import QuizResult, TelegramUser


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
        "is_first_visit_display",
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
        "is_first_visit",
        "notification_intro_seen",
    )
    ordering = ("-created_at",)
    actions = ["delete_selected", "send_morning_touch_test", "send_day_touch_test", "send_evening_touch_test"]
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
        "is_first_visit",
        "notification_intro_seen",
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
        (
            "Статус пользователя",
            {
                "fields": (
                    "is_first_visit",
                    "notification_intro_seen",
                )
            },
        ),
    )
    inlines = (QuizResultInline,)

    # --------------------------------------------------------------------- utils
    def latest_quiz_result(self, obj):
        result = obj.quiz_results.order_by("-created_at").first()
        if not result:
            return "—"
        return (
            f"Э:{result.energy} Сч:{result.happiness} Сон:{result.sleep_quality} "
            f"Отн:{result.relationships_quality} Бал:{result.life_balance} Стр:{result.strategy_level}"
        )

    latest_quiz_result.short_description = "Стартовый портрет"

    def is_first_visit_display(self, obj):
        """Отображение статуса первого визита"""
        if obj.is_first_visit:
            return "🆕 Первый визит"
        return "✅ Не первый раз"
    
    is_first_visit_display.short_description = "Статус визита"
    is_first_visit_display.boolean = False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    # --------------------------------------------------------------------- actions
    def _fetch_users(self, queryset):
        from database.session import SessionLocal
        from models.user import User
        from sqlalchemy import select

        with SessionLocal() as session:
            if queryset.exists():
                telegram_ids = [obj.telegram_id for obj in queryset]
                stmt = select(User.id, User.telegram_id).where(User.telegram_id.in_(telegram_ids))
            else:
                stmt = select(User.id, User.telegram_id).where(
                    User.subscription_type.in_({"trial", "paid", "free_week", "monthly"})
                )
            result = session.execute(stmt)
            return list(result.all())

    def send_morning_touch_test(self, request, queryset):
        """Отправить утреннее касание выбранным пользователям (для теста, без проверки времени)"""
        try:
            from services.morning_touch import _get_content_for_user, _send_touch_content, _mark_users_sent

            async def run_touch():
                import limited_aiogram
                bot = limited_aiogram.LimitedBot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    users = await asyncio.to_thread(self._fetch_users, queryset)
                    if not users:
                        return 0

                    bot_info = await bot.get_me()
                    bot_id = bot_info.id

                    sent_count = 0
                    sent_user_ids = []
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(_get_content_for_user, user_id, target_date)
                            if content:
                                await _send_touch_content(bot, telegram_id, content, bot_id=bot_id)
                            sent_user_ids.append(user_id)
                            sent_count += 1
                        except Exception as exc:  # pylint: disable=broad-except
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить утреннее сообщение пользователю %s: %s", telegram_id, exc)

                    await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
                    return sent_count
                finally:
                    await bot.session.close()

            sent_count = asyncio.run(run_touch())
            self.message_user(request, f"Утреннее касание отправлено {sent_count} пользователям", messages.SUCCESS)
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            self.message_user(
                request,
                f"Ошибка при отправке утреннего касания: {str(exc)}\n{traceback.format_exc()}",
                messages.ERROR,
            )

    send_morning_touch_test.short_description = "📤 Отправить утреннее касание (тест)"

    def send_day_touch_test(self, request, queryset):
        """Отправить дневное касание всем активным пользователям (для теста, без проверки времени)"""
        try:
            from services.day_touch import _get_content_for_user, _build_day_keyboard
            from core.texts import TEXTS

            async def run_touch():
                import limited_aiogram
                bot = limited_aiogram.LimitedBot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    users = await asyncio.to_thread(self._fetch_users, queryset)
                    if not users:
                        return 0

                    sent_count = 0
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(_get_content_for_user, user_id, target_date)
                            if not content:
                                continue
                            keyboard = _build_day_keyboard()
                            await bot.send_message(telegram_id, TEXTS["day_touch_prompt"], reply_markup=keyboard)
                            if content.video_url:
                                await bot.send_message(telegram_id, content.video_url)
                            sent_count += 1
                        except Exception as exc:  # pylint: disable=broad-except
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить дневное сообщение %s: %s", telegram_id, exc)

                    return sent_count
                finally:
                    await bot.session.close()

            sent_count = asyncio.run(run_touch())
            self.message_user(request, f"Дневное касание отправлено {sent_count} активным пользователям", messages.SUCCESS)
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            self.message_user(
                request,
                f"Ошибка при отправке дневного касания: {str(exc)}\n{traceback.format_exc()}",
                messages.ERROR,
            )

    send_day_touch_test.short_description = "📤 Отправить дневное касание (тест)"

    def send_evening_touch_test(self, request, queryset):
        """Отправить вечернее касание всем активным пользователям (для теста, без проверки времени)"""
        try:
            from services.evening_touch import _get_content_for_user, _send_evening_content, _send_first_rating_question

            async def run_touch():
                import limited_aiogram
                bot = limited_aiogram.LimitedBot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    bot_info = await bot.get_me()
                    bot_id = bot_info.id

                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    users = await asyncio.to_thread(self._fetch_users, queryset)
                    if not users:
                        return 0

                    sent_count = 0
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(_get_content_for_user, user_id, target_date)
                            if not content:
                                continue
                            await _send_evening_content(bot, telegram_id, content)
                            await _send_first_rating_question(
                                bot, telegram_id, bot_id=bot_id, touch_content_id=content.id
                            )
                            sent_count += 1
                        except Exception as exc:  # pylint: disable=broad-except
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить вечернее сообщение %s: %s", telegram_id, exc)

                    return sent_count
                finally:
                    await bot.session.close()

            sent_count = asyncio.run(run_touch())
            self.message_user(request, f"Вечернее касание отправлено {sent_count} активным пользователям", messages.SUCCESS)
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            self.message_user(
                request,
                f"Ошибка при отправке вечернего касания: {str(exc)}\n{traceback.format_exc()}",
                messages.ERROR,
            )

    send_evening_touch_test.short_description = "📤 Отправить вечернее касание (тест)"

