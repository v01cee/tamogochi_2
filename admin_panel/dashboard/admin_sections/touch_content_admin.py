"""TouchContent admin configuration and broadcast action."""

import asyncio
import json
import logging
from pathlib import Path

import redis
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from django.contrib import admin, messages

from core.config import settings
from ..models import TouchContent


@admin.register(TouchContent)
class TouchContentAdmin(admin.ModelAdmin):
    list_display = (
        "course_day",
        "title",
        "touch_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("touch_type", "is_active", "course_day")
    search_fields = ("title", "questions")
    ordering = ("course_day__day_number", "touch_type", "-updated_at")
    readonly_fields = ("title", "created_at", "updated_at", "order_index")
    autocomplete_fields = ("course_day",)
    actions = ["send_touch_to_all_users"]
    fieldsets = (
        (
            "Общее",
            {
                "fields": (
                    "course_day",
                    "touch_type",
                    "is_active",
                )
            },
        ),
        (
            "Контент",
            {
                "fields": (
                    "video_file",
                    "summary",
                    "questions",
                )
            },
        ),
        (
            "Служебное",
            {
                "fields": (
                    "order_index",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def send_touch_to_all_users(self, request, queryset):
        """Отправить выбранное касание всем активным пользователям"""
        if queryset.count() != 1:
            self.message_user(request, "Пожалуйста, выберите ровно одно касание для рассылки", messages.ERROR)
            return

        touch_content = queryset.first()

        try:
            from database.session import SessionLocal
            from models.user import User

            async def run_send():
                import limited_aiogram
                bot = limited_aiogram.LimitedBot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
                bot_info = await bot.get_me()
                bot_id = bot_info.id

                logger = logging.getLogger(__name__)
                logger.info(f"[ADMIN] Bot ID: {bot_id}")

                redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password,
                    db=settings.redis_db,
                    decode_responses=True,
                )
                try:
                    def fetch_all_users():
                        from sqlalchemy import select

                        with SessionLocal() as session:
                            stmt = (
                                select(User.id, User.telegram_id)
                                .where(User.telegram_id.is_not(None))
                            )
                            result = session.execute(stmt)
                            return list(result.all())

                    users = await asyncio.to_thread(fetch_all_users)
                    if not users:
                        logger.warning("[ADMIN] Нет пользователей с telegram_id для рассылки")
                        return 0

                    sent_count = 0
                    for user_id, telegram_id in users:
                        try:
                            await self._send_touch(bot, bot_id, telegram_id, touch_content, redis_client, logger)
                            sent_count += 1
                        except Exception as exc:  # pylint: disable=broad-except
                            logger.warning("Не удалось отправить касание пользователю %s: %s", telegram_id, exc)

                    return sent_count
                finally:
                    await bot.session.close()

            sent_count = asyncio.run(run_send())
            self.message_user(
                request,
                f"Касание '{touch_content.title}' отправлено {sent_count} пользователям",
                messages.SUCCESS,
            )
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            self.message_user(
                request,
                f"Ошибка при отправке касания: {str(exc)}\n{traceback.format_exc()}",
                messages.ERROR,
            )

    send_touch_to_all_users.short_description = "📤 Отправить касание всем пользователям"

    # ------------------------------------------------------------------ utils
    async def _send_touch(self, bot, bot_id, telegram_id, touch_content, redis_client, logger):
        from services.evening_touch import _send_first_rating_question

        touch_type = touch_content.touch_type
        logger.info(f"[ADMIN] Отправляем касание типа: {touch_type}")

        if touch_type == "day":
            await self._send_day_touch(bot, telegram_id, touch_content, logger)
            return

        if touch_type == "evening":
            await self._send_evening_touch(bot, telegram_id, touch_content, bot_id, logger)
            return

        await self._send_morning_touch(bot, telegram_id, touch_content, bot_id, redis_client, logger)

    async def _send_day_touch(self, bot, telegram_id, touch_content, logger):
        if touch_content.summary:
            summary_text = touch_content.summary.strip()
            logger.info(f"[ADMIN] Отправляем описание для day_touch: {summary_text[:100]}...")
            await bot.send_message(telegram_id, summary_text)
            logger.info("[ADMIN] Описание для day_touch успешно отправлено")
        else:
            logger.warning("[ADMIN] Нет описания (summary) для day_touch")

        if touch_content.video_url:
            from aiogram.utils.keyboard import InlineKeyboardBuilder

            await asyncio.sleep(5)
            keyboard_builder = InlineKeyboardBuilder()
            if settings.community_chat_url:
                keyboard_builder.button(text="Перейти в чат", url=settings.community_chat_url)
            else:
                keyboard_builder.button(text="Перейти в чат", callback_data="chat_placeholder")
            keyboard_builder.button(text="В меню «Стратегия дня»", callback_data="day_strategy")
            keyboard_builder.adjust(1, 1)
            keyboard = keyboard_builder.as_markup()

            video_url = touch_content.video_url.strip()
            logger.info(f"[ADMIN] Отправляем ссылку на видео для day_touch с кнопками: {video_url}")
            await bot.send_message(telegram_id, video_url, reply_markup=keyboard)
            logger.info("[ADMIN] Ссылка на видео для day_touch с кнопками успешно отправлена")
        else:
            logger.warning("[ADMIN] Нет ссылки на видео (video_url) для day_touch")

        logger.info("[ADMIN] Для day_touch вопросы не отправляются")

    async def _send_evening_touch(self, bot, telegram_id, touch_content, bot_id, logger):
        from services.evening_touch import _send_evening_content, _send_first_rating_question

        logger.info("[ADMIN] Касание типа 'evening' - отправляем видео или текст")
        await _send_evening_content(bot, telegram_id, touch_content)
        await _send_first_rating_question(bot, telegram_id, bot_id=bot_id, touch_content_id=touch_content.id)
        logger.info("[ADMIN] Первый вопрос оценки отправлен")

    async def _send_morning_touch(self, bot, telegram_id, touch_content, bot_id, redis_client, logger):
        caption = touch_content.summary.strip() if touch_content.summary else None
        video_sent = False

        if touch_content.video_file:
            try:
                video_file_path = touch_content.video_file.path
                if Path(video_file_path).exists():
                    await bot.send_video(telegram_id, FSInputFile(video_file_path), caption=caption)
                    video_sent = True
                    logger.info("[ADMIN] Видео файл успешно отправлен")
            except Exception as file_exc:  # pylint: disable=broad-except
                logger.warning("Не удалось отправить видео файл: %s", file_exc)

        if not video_sent and touch_content.video_url:
            await bot.send_video(telegram_id, touch_content.video_url, caption=caption)
            video_sent = True
            logger.info("[ADMIN] Видео по URL успешно отправлено")

        if not video_sent and touch_content.summary:
            await bot.send_message(telegram_id, touch_content.summary.strip())
            logger.info("[ADMIN] Отправлено только описание (видео отсутствует)")

        await bot.send_message(
            telegram_id,
            "Пожалуйста, ответь на эти вопросы — напиши или наговори голосом свои мысли. Мы соберём их в твою личную карту стратегий",
        )
        logger.info("[ADMIN] Текст с просьбой ответить на вопросы отправлен")

        if touch_content.questions:
            await asyncio.sleep(5)
            await self._handle_questions(bot, telegram_id, touch_content, bot_id, redis_client, logger)

    async def _handle_questions(self, bot, telegram_id, touch_content, bot_id, redis_client, logger):
        questions_text_raw = touch_content.questions or ""
        questions_text = questions_text_raw.strip()
        split_lines = questions_text.split("\n")
        questions_list = [line.strip() for line in split_lines if line.strip()]

        if not questions_list:
            logger.warning("[ADMIN] ✗ Список вопросов пуст после разделения")
            logger.warning("[ADMIN] Исходный текст вопросов был: %s", questions_text[:200])
            logger.warning("[ADMIN] ===== СОЗДАНИЕ СПИСКА ВОПРОСОВ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЕМ =====")
            return

        first_question = questions_list[0]
        logger.info(f"[ADMIN] Отправляем первый вопрос пользователю: {first_question[:100]}...")
        await bot.send_message(telegram_id, first_question)
        logger.info("[ADMIN] Первый вопрос успешно отправлен")

        state_key = f"fsm:{bot_id}:{telegram_id}:state"
        data_key = f"fsm:{bot_id}:{telegram_id}:data"
        redis_data = {
            "touch_content_id": touch_content.id,
            "questions_list": questions_list,
            "current_question_index": 0,
            "answers": [],
        }
        json_data = json.dumps(redis_data, ensure_ascii=False)

        redis_client.set(state_key, "TouchQuestionStates:waiting_for_answer", ex=3600)
        redis_client.set(data_key, json_data, ex=3600)
        logger.info("[ADMIN] Данные сохранены в Redis")
