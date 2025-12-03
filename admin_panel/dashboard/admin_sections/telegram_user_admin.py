"""TelegramUser admin configuration and related actions."""

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from django.contrib import admin, messages

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта core.config
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.config import settings as core_settings
from ..models import (
    QuizResult,
    TelegramUser,
    TouchAnswer,
    EveningReflection,
    EveningRating,
    SaturdayReflection,
)


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


class TouchAnswerInline(admin.TabularInline):
    model = TouchAnswer
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "touch_content",
        "touch_date",
        "question_index",
        "answer_text",
        "created_at",
    )
    ordering = ("-touch_date", "question_index")
    show_change_link = True
    fk_name = "user"


class EveningReflectionInline(admin.TabularInline):
    model = EveningReflection
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "reflection_date",
        "reflection_text",
        "created_at",
    )
    ordering = ("-reflection_date",)
    show_change_link = True
    fk_name = "user"


class EveningRatingInline(admin.TabularInline):
    model = EveningRating
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "rating_date",
        "rating_energy",
        "rating_happiness",
        "rating_progress",
        "created_at",
    )
    ordering = ("-rating_date",)
    show_change_link = True
    fk_name = "user"


class SaturdayReflectionInline(admin.TabularInline):
    model = SaturdayReflection
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = (
        "reflection_date",
        "segments_completed",
        "created_at",
    )
    ordering = ("-reflection_date",)
    show_change_link = True
    fk_name = "user"


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
    actions = [
        "delete_selected",
        "grant_30_day_subscription",
        "send_morning_touch_test",
        "send_day_touch_test",
        "send_evening_touch_test",
        "send_saturday_touch_test",
    ]
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
    inlines = (
        QuizResultInline,
        TouchAnswerInline,
        EveningReflectionInline,
        EveningRatingInline,
        SaturdayReflectionInline,
    )

    # --------------------------------------------------------------------- utils
    def latest_quiz_result(self, obj):
        result = obj.quiz_results.order_by("-created_at").first()
        if not result:
            return "—"
        return (
            f"Э: {result.energy}  Сч: {result.happiness}  Сон: {result.sleep_quality}  "
            f"Отн: {result.relationships_quality}  Бал: {result.life_balance}  Стр: {result.strategy_level}"
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

    def grant_30_day_subscription(self, request, queryset):
        """
        Выдать подписку на 30 дней (4 недели) выбранным пользователям.

        Обновляем реальные записи в таблице users через SQLAlchemy-модель User:
        - subscription_type = "monthly"
        - subscription_paid_at = сейчас
        - если subscription_started_at пустой — ставим сейчас
        - сбрасываем флаги отправки касаний, чтобы бот начал касания заново
        """
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from database.session import SessionLocal
        from models.user import User
        from sqlalchemy import select

        tz = ZoneInfo(core_settings.timezone or "Europe/Moscow")
        now = datetime.now(tz=tz)

        telegram_ids = list(queryset.values_list("telegram_id", flat=True))
        if not telegram_ids:
            self.message_user(
                request,
                "Не выбрано ни одного пользователя",
                messages.WARNING,
            )
            return

        updated_count = 0
        with SessionLocal() as session:
            stmt = select(User).where(User.telegram_id.in_(telegram_ids))
            users = session.execute(stmt).scalars().all()
            for user in users:
                user.subscription_type = "monthly"
                user.subscription_paid_at = now
                if user.subscription_started_at is None:
                    user.subscription_started_at = now

                user.morning_touch_sent_at = None
                user.day_touch_sent_at = None
                user.evening_touch_sent_at = None

                updated_count += 1

            session.commit()

        self.message_user(
            request,
            f"Подписка на 30 дней выдана {updated_count} пользователям(ю).",
            messages.SUCCESS,
        )

    grant_30_day_subscription.short_description = "🎟 Выдать подписку на 30 дней (monthly)"

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
                if not core_settings.bot_token:
                    raise ValueError("BOT_TOKEN не установлен в переменных окружения")
                bot = limited_aiogram.LimitedBot(token=core_settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    tz = ZoneInfo("Europe/Moscow")
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
                if not core_settings.bot_token:
                    raise ValueError("BOT_TOKEN не установлен в переменных окружения")
                bot = limited_aiogram.LimitedBot(token=core_settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    tz = ZoneInfo("Europe/Moscow")
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
                                from aiogram.types import LinkPreviewOptions
                                await bot.send_message(telegram_id, content.video_url, link_preview_options=LinkPreviewOptions(is_disabled=True))
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
                if not core_settings.bot_token:
                    raise ValueError("BOT_TOKEN не установлен в переменных окружения")
                bot = limited_aiogram.LimitedBot(token=core_settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    bot_info = await bot.get_me()
                    bot_id = bot_info.id

                    tz = ZoneInfo("Europe/Moscow")
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

    def send_saturday_touch_test(self, request, queryset):
        """Отправить сообщение о стратсубботе выбранным пользователям (для теста, без проверки дня недели)"""
        try:
            from core.texts import get_booking_text
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode

            async def run_touch():
                import limited_aiogram
                if not core_settings.bot_token:
                    raise ValueError("BOT_TOKEN не установлен в переменных окружения")
                bot = limited_aiogram.LimitedBot(token=core_settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                try:
                    # Получаем пользователей из queryset или всех активных
                    users = await asyncio.to_thread(self._fetch_users, queryset)
                    
                    if not users:
                        return 0

                    # Получаем текст сообщения
                    message_text = get_booking_text("saturday_reflection")
                    
                    # Создаем клавиатуру с кнопкой "Начать"
                    keyboard_builder = InlineKeyboardBuilder()
                    keyboard_builder.button(text="Начать", callback_data="saturday_reflection_start")
                    keyboard_builder.adjust(1)
                    keyboard = keyboard_builder.as_markup()

                    sent_count = 0
                    for user_id, telegram_id in users:
                        try:
                            await bot.send_message(telegram_id, message_text, reply_markup=keyboard)
                            sent_count += 1
                        except Exception as exc:  # pylint: disable=broad-except
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить сообщение о стратсубботе пользователю %s: %s", telegram_id, exc)

                    return sent_count
                finally:
                    await bot.session.close()

            sent_count = asyncio.run(run_touch())
            self.message_user(request, f"Сообщение о стратсубботе отправлено {sent_count} пользователям", messages.SUCCESS)
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            self.message_user(
                request,
                f"Ошибка при отправке сообщения о стратсубботе: {str(exc)}\n{traceback.format_exc()}",
                messages.ERROR,
            )

    send_saturday_touch_test.short_description = "📤 Отправить стратсубботу (тест)"

