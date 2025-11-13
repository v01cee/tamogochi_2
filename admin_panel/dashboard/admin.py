import asyncio
import os
import sys
from django.contrib import admin
from django.contrib import messages

from .models import CourseDay, QuizResult, TelegramUser, TouchContent

# Добавляем путь к корню проекта для импорта модулей бота
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


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
        return True

    def send_morning_touch_test(self, request, queryset):
        """Отправить утреннее касание выбранным пользователям (для теста, без проверки времени)"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            from core.config import settings
            from database.session import SessionLocal
            from models.user import User
            from services.morning_touch import _get_content_for_user, _send_touch_content, _mark_users_sent
            from core.texts import TEXTS
            from datetime import datetime
            from zoneinfo import ZoneInfo
            import asyncio
            
            async def run_touch():
                bot = Bot(
                    token=settings.bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                try:
                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    
                    # Если выбраны пользователи - используем их, иначе всех активных
                    def fetch_users():
                        with SessionLocal() as session:
                            from sqlalchemy import select
                            if queryset.exists():
                                # Используем выбранных пользователей
                                telegram_ids = [obj.telegram_id for obj in queryset]
                                stmt = select(User.id, User.telegram_id).where(
                                    User.telegram_id.in_(telegram_ids)
                                )
                            else:
                                # Если не выбраны - всех активных с любой подпиской
                                stmt = select(User.id, User.telegram_id).where(
                                    User.subscription_type.in_({"trial", "paid", "free_week", "monthly"})
                                )
                            result = session.execute(stmt)
                            return list(result.all())
                    
                    users = await asyncio.to_thread(fetch_users)
                    if not users:
                        return 0
                    
                    sent_count = 0
                    sent_user_ids = []
                    
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(
                                _get_content_for_user,
                                user_id,
                                target_date,
                            )
                            
                            if content:
                                await _send_touch_content(bot, telegram_id, content)
                            await bot.send_message(telegram_id, TEXTS["touch_8_1_morning_prompt"])
                            sent_user_ids.append(user_id)
                            sent_count += 1
                        except Exception as exc:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(
                                "Не удалось отправить утреннее сообщение пользователю %s: %s",
                                telegram_id,
                                exc,
                            )
                    
                    await asyncio.to_thread(_mark_users_sent, sent_user_ids, now)
                    return sent_count
                finally:
                    await bot.session.close()
            
            sent_count = asyncio.run(run_touch())
            self.message_user(
                request,
                f"Утреннее касание отправлено {sent_count} пользователям",
                messages.SUCCESS
            )
        except Exception as e:
            import traceback
            self.message_user(
                request,
                f"Ошибка при отправке утреннего касания: {str(e)}\n{traceback.format_exc()}",
                messages.ERROR
            )
    
    send_morning_touch_test.short_description = "📤 Отправить утреннее касание (тест)"

    def send_day_touch_test(self, request, queryset):
        """Отправить дневное касание всем активным пользователям (для теста, без проверки времени)"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            from core.config import settings
            from database.session import SessionLocal
            from models.user import User
            from services.day_touch import _get_content_for_user, _build_day_keyboard
            from core.texts import TEXTS
            from datetime import datetime
            from zoneinfo import ZoneInfo
            import asyncio
            
            async def run_touch():
                bot = Bot(
                    token=settings.bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                try:
                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    
                    # Если выбраны пользователи - используем их, иначе всех активных
                    def fetch_users():
                        with SessionLocal() as session:
                            from sqlalchemy import select
                            if queryset.exists():
                                # Используем выбранных пользователей
                                telegram_ids = [obj.telegram_id for obj in queryset]
                                stmt = select(User.id, User.telegram_id).where(
                                    User.telegram_id.in_(telegram_ids)
                                )
                            else:
                                # Если не выбраны - всех активных с любой подпиской
                                stmt = select(User.id, User.telegram_id).where(
                                    User.subscription_type.in_({"trial", "paid", "free_week", "monthly"})
                                )
                            result = session.execute(stmt)
                            return list(result.all())
                    
                    users = await asyncio.to_thread(fetch_users)
                    if not users:
                        return 0
                    
                    sent_count = 0
                    
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(
                                _get_content_for_user,
                                user_id,
                                target_date,
                            )
                            
                            if not content:
                                continue
                            
                            keyboard = _build_day_keyboard()
                            await bot.send_message(telegram_id, TEXTS["day_touch_prompt"], reply_markup=keyboard)
                            if content.video_url:
                                await bot.send_message(telegram_id, content.video_url)
                            sent_count += 1
                        except Exception as exc:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить дневное сообщение %s: %s", telegram_id, exc)
                    
                    return sent_count
                finally:
                    await bot.session.close()
            
            sent_count = asyncio.run(run_touch())
            self.message_user(
                request,
                f"Дневное касание отправлено {sent_count} активным пользователям",
                messages.SUCCESS
            )
        except Exception as e:
            import traceback
            self.message_user(
                request,
                f"Ошибка при отправке дневного касания: {str(e)}\n{traceback.format_exc()}",
                messages.ERROR
            )
    
    send_day_touch_test.short_description = "📤 Отправить дневное касание (тест)"

    def send_evening_touch_test(self, request, queryset):
        """Отправить вечернее касание всем активным пользователям (для теста, без проверки времени)"""
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            from core.config import settings
            from database.session import SessionLocal
            from models.user import User
            from services.evening_touch import _get_content_for_user, _build_evening_keyboard
            from core.texts import TEXTS
            from datetime import datetime
            from zoneinfo import ZoneInfo
            import asyncio
            
            async def run_touch():
                bot = Bot(
                    token=settings.bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                try:
                    tz = ZoneInfo(settings.timezone)
                    now = datetime.now(tz=tz)
                    target_date = now.date()
                    
                    # Если выбраны пользователи - используем их, иначе всех активных
                    def fetch_users():
                        with SessionLocal() as session:
                            from sqlalchemy import select
                            if queryset.exists():
                                # Используем выбранных пользователей
                                telegram_ids = [obj.telegram_id for obj in queryset]
                                stmt = select(User.id, User.telegram_id).where(
                                    User.telegram_id.in_(telegram_ids)
                                )
                            else:
                                # Если не выбраны - всех активных с любой подпиской
                                stmt = select(User.id, User.telegram_id).where(
                                    User.subscription_type.in_({"trial", "paid", "free_week", "monthly"})
                                )
                            result = session.execute(stmt)
                            return list(result.all())
                    
                    users = await asyncio.to_thread(fetch_users)
                    if not users:
                        return 0
                    
                    sent_count = 0
                    
                    for user_id, telegram_id in users:
                        try:
                            content = await asyncio.to_thread(
                                _get_content_for_user,
                                user_id,
                                target_date,
                            )
                            
                            if not content:
                                continue
                            
                            keyboard = _build_evening_keyboard()
                            await bot.send_message(
                                telegram_id,
                                TEXTS["evening_touch_prompt"],
                                reply_markup=keyboard,
                            )
                            if content.summary:
                                await bot.send_message(telegram_id, content.summary.strip())
                            if content.questions:
                                await bot.send_message(telegram_id, content.questions.strip())
                            sent_count += 1
                        except Exception as exc:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning("Не удалось отправить вечернее сообщение %s: %s", telegram_id, exc)
                    
                    return sent_count
                finally:
                    await bot.session.close()
            
            sent_count = asyncio.run(run_touch())
            self.message_user(
                request,
                f"Вечернее касание отправлено {sent_count} активным пользователям",
                messages.SUCCESS
            )
        except Exception as e:
            import traceback
            self.message_user(
                request,
                f"Ошибка при отправке вечернего касания: {str(e)}\n{traceback.format_exc()}",
                messages.ERROR
            )
    
    send_evening_touch_test.short_description = "📤 Отправить вечернее касание (тест)"


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
        # Проверяем, есть ли фильтр по is_active в GET параметрах
        if 'is_active__exact' not in request.GET:
            # Если фильтр не установлен, показываем только активные
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
                    "video_url",
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
    readonly_fields = ("title", "created_at", "updated_at", "order_index")

    def send_touch_to_all_users(self, request, queryset):
        """Отправить выбранное касание всем активным пользователям"""
        if queryset.count() != 1:
            self.message_user(
                request,
                "Пожалуйста, выберите ровно одно касание для рассылки",
                messages.ERROR
            )
            return
        
        touch_content = queryset.first()
        
        try:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            from aiogram.types import FSInputFile
            from core.config import settings
            from database.session import SessionLocal
            from models.user import User
            from pathlib import Path
            import asyncio
            import json
            import redis
            
            async def run_send():
                bot = Bot(
                    token=settings.bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                # Получаем bot.id после инициализации
                bot_info = await bot.get_me()
                bot_id = bot_info.id
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[ADMIN] Bot ID: {bot_id}")
                
                # Подключаемся к Redis для хранения состояния
                redis_client = redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password,
                    db=settings.redis_db,
                    decode_responses=True
                )
                try:
                    # Получаем всех активных пользователей
                    def fetch_all_users():
                        with SessionLocal() as session:
                            from sqlalchemy import select
                            stmt = select(User.id, User.telegram_id).where(
                                User.subscription_type.in_({"trial", "paid", "free_week", "monthly"})
                            )
                            result = session.execute(stmt)
                            return list(result.all())
                    
                    users = await asyncio.to_thread(fetch_all_users)
                    if not users:
                        return 0
                    
                    sent_count = 0
                    
                    for user_id, telegram_id in users:
                        try:
                            import logging
                            logger = logging.getLogger(__name__)
                            
                            # Проверяем тип касания
                            touch_type = touch_content.touch_type
                            logger.info(f"[ADMIN] Отправляем касание типа: {touch_type}")
                            
                            # Для касания "day" отправляем только описание и ссылку на видео, без вопросов
                            if touch_type == "day":
                                logger.info(f"[ADMIN] Касание типа 'day' - отправляем описание и ссылку на видео")
                                
                                # Шаг 1: Отправляем описание (summary) из админки
                                if touch_content.summary:
                                    summary_text = touch_content.summary.strip()
                                    logger.info(f"[ADMIN] Отправляем описание для day_touch: {summary_text[:100]}...")
                                    await bot.send_message(telegram_id, summary_text)
                                    logger.info(f"[ADMIN] Описание для day_touch успешно отправлено")
                                else:
                                    logger.warning(f"[ADMIN] Нет описания (summary) для day_touch")
                                
                                # Шаг 2: Через 5 секунд отправляем ссылку на видео с кнопками
                                if touch_content.video_url:
                                    logger.info(f"[ADMIN] Ждем 5 секунд перед отправкой ссылки на видео")
                                    await asyncio.sleep(5)
                                    
                                    # Создаем клавиатуру с кнопками для day_touch
                                    from aiogram.utils.keyboard import InlineKeyboardBuilder
                                    
                                    keyboard_builder = InlineKeyboardBuilder()
                                    # Первая кнопка: "Перейти в чат" (если есть URL - ссылка, иначе заглушка)
                                    if settings.community_chat_url:
                                        keyboard_builder.button(text="Перейти в чат", url=settings.community_chat_url)
                                    else:
                                        # Заглушка для кнопки "Перейти в чат"
                                        keyboard_builder.button(text="Перейти в чат", callback_data="chat_placeholder")
                                    # Вторая кнопка: "В меню «Стратегия дня»"
                                    keyboard_builder.button(text="В меню «Стратегия дня»", callback_data="day_strategy")
                                    keyboard_builder.adjust(1, 1)
                                    keyboard = keyboard_builder.as_markup()
                                    
                                    video_url = touch_content.video_url.strip()
                                    logger.info(f"[ADMIN] Отправляем ссылку на видео для day_touch с кнопками: {video_url}")
                                    await bot.send_message(telegram_id, video_url, reply_markup=keyboard)
                                    logger.info(f"[ADMIN] Ссылка на видео для day_touch с кнопками успешно отправлена")
                                else:
                                    logger.warning(f"[ADMIN] Нет ссылки на видео (video_url) для day_touch")
                                
                                # Для day_touch не отправляем вопросы
                                logger.info(f"[ADMIN] Для day_touch вопросы не отправляются")
                            
                            else:
                                # Для других типов касаний (morning, evening) отправляем видео и вопросы
                                logger.info(f"[ADMIN] Касание типа '{touch_type}' - отправляем видео и вопросы")
                                
                                # Формируем caption: описание (summary) отправляется как текст к видео
                                caption = touch_content.summary.strip() if touch_content.summary else None
                                
                                # Отправляем видео с описанием в caption (видео всегда есть)
                                video_sent = False
                                if touch_content.video_file:
                                    # Django FileField - получаем путь к файлу
                                    try:
                                        video_file_path = touch_content.video_file.path
                                        if Path(video_file_path).exists():
                                            await bot.send_video(
                                                telegram_id,
                                                FSInputFile(video_file_path),
                                                caption=caption,
                                            )
                                            video_sent = True
                                            logger.info(f"[ADMIN] Видео файл успешно отправлен")
                                    except Exception as file_exc:
                                        logger.warning(f"Не удалось отправить видео файл: {file_exc}")
                                
                                # Если файл не отправился, пробуем URL
                                if not video_sent and touch_content.video_url:
                                    await bot.send_video(
                                        telegram_id,
                                        touch_content.video_url,
                                        caption=caption,
                                    )
                                    video_sent = True
                                    logger.info(f"[ADMIN] Видео по URL успешно отправлено")
                                
                                # После отправки видео отправляем фиксированный текст
                                await bot.send_message(
                                    telegram_id,
                                    "Пожалуйста, ответь на эти вопросы — напиши или наговори голосом свои мысли. Мы соберём их в твою личную карту стратегий"
                                )
                                logger.info(f"[ADMIN] Текст с просьбой ответить на вопросы отправлен")
                                
                                # Через 5 секунд отправляем первый вопрос из поля "Вопросы"
                                if touch_content.questions:
                                    logger.info(f"[ADMIN] ===== НАЧАЛО СОЗДАНИЯ СПИСКА ВОПРОСОВ =====")
                                    logger.info(f"[ADMIN] Touch Content ID: {touch_content.id}")
                                    logger.info(f"[ADMIN] Пользователь: {telegram_id}")
                                    logger.info(f"[ADMIN] Проверяем наличие вопросов в touch_content.questions")
                                    
                                    await asyncio.sleep(5)
                                    
                                    # Разделяем вопросы по переносу строки
                                    logger.info(f"[ADMIN] Получаем исходный текст вопросов из базы данных")
                                    questions_text_raw = touch_content.questions
                                    logger.info(f"[ADMIN] Исходный текст (raw, длина {len(questions_text_raw) if questions_text_raw else 0}): {questions_text_raw[:500] if questions_text_raw else 'None'}...")
                                    
                                    questions_text = questions_text_raw.strip() if questions_text_raw else ""
                                    logger.info(f"[ADMIN] Текст после strip (длина {len(questions_text)}): {questions_text[:500]}...")
                                    
                                    # Разделяем по переносу строки
                                    logger.info(f"[ADMIN] Разделяем текст по символу переноса строки (\\n)")
                                    split_lines = questions_text.split('\n')
                                    logger.info(f"[ADMIN] Получено строк после split: {len(split_lines)}")
                                    
                                    # Логируем каждую строку до фильтрации
                                    for idx, line in enumerate(split_lines):
                                        logger.info(f"[ADMIN] Строка #{idx + 1} (до strip): длина={len(line)}, пустая={not line.strip()}, содержимое: {repr(line[:100])}")
                                    
                                    # Фильтруем и очищаем вопросы
                                    logger.info(f"[ADMIN] Фильтруем и очищаем вопросы (убираем пустые строки)")
                                    questions_list = []
                                    for idx, line in enumerate(split_lines):
                                        stripped = line.strip()
                                        if stripped:
                                            questions_list.append(stripped)
                                            logger.info(f"[ADMIN] Вопрос #{len(questions_list)} добавлен (из строки #{idx + 1}): длина={len(stripped)}, первые 100 символов: {stripped[:100]}")
                                        else:
                                            logger.info(f"[ADMIN] Строка #{idx + 1} пропущена (пустая после strip)")
                                    
                                    logger.info(f"[ADMIN] Итоговый список вопросов: всего {len(questions_list)} вопросов")
                                    
                                    # Детальное логирование каждого вопроса
                                    for idx, question in enumerate(questions_list):
                                        logger.info(f"[ADMIN] Вопрос #{idx + 1}/{len(questions_list)}: длина={len(question)}, текст: {question[:200]}...")
                                    
                                    if questions_list:
                                        first_question = questions_list[0]
                                        logger.info(f"[ADMIN] Отправляем первый вопрос пользователю: {first_question[:100]}...")
                                        await bot.send_message(telegram_id, first_question)
                                        logger.info(f"[ADMIN] Первый вопрос успешно отправлен")
                                        
                                        # Сохраняем информацию о касании и вопросах в Redis для обработки ответов
                                        state_key = f"fsm:{bot_id}:{telegram_id}:state"
                                        data_key = f"fsm:{bot_id}:{telegram_id}:data"
                                        
                                        logger.info(f"[ADMIN] Подготавливаем данные для сохранения в Redis")
                                        logger.info(f"[ADMIN] State key: {state_key}")
                                        logger.info(f"[ADMIN] Data key: {data_key}")
                                        logger.info(f"[ADMIN] Touch Content ID: {touch_content.id}")
                                        logger.info(f"[ADMIN] Количество вопросов для сохранения: {len(questions_list)}")
                                        logger.info(f"[ADMIN] Начальный индекс вопроса: 0")
                                        
                                        redis_data = {
                                            "touch_content_id": touch_content.id,
                                            "questions_list": questions_list,
                                            "current_question_index": 0,
                                            "answers": []
                                        }
                                        
                                        # Логируем структуру данных перед сохранением
                                        logger.info(f"[ADMIN] Структура данных для Redis:")
                                        logger.info(f"[ADMIN]   - touch_content_id: {redis_data['touch_content_id']}")
                                        logger.info(f"[ADMIN]   - questions_list: список из {len(redis_data['questions_list'])} элементов")
                                        logger.info(f"[ADMIN]   - current_question_index: {redis_data['current_question_index']}")
                                        logger.info(f"[ADMIN]   - answers: список из {len(redis_data['answers'])} элементов")
                                        
                                        # Сериализуем в JSON для логирования
                                        json_data = json.dumps(redis_data, ensure_ascii=False)
                                        logger.info(f"[ADMIN] JSON данные (первые 500 символов): {json_data[:500]}...")
                                        logger.info(f"[ADMIN] Размер JSON данных: {len(json_data)} символов")
                                        
                                        logger.info(f"[ADMIN] Сохраняем состояние в Redis (ключ: {state_key})")
                                        redis_client.set(state_key, "TouchQuestionStates:waiting_for_answer", ex=3600)  # 1 час
                                        logger.info(f"[ADMIN] Состояние сохранено в Redis")
                                        
                                        logger.info(f"[ADMIN] Сохраняем данные в Redis (ключ: {data_key}, TTL: 3600 сек)")
                                        redis_client.set(
                                            data_key,
                                            json_data,
                                            ex=3600  # 1 час
                                        )
                                        logger.info(f"[ADMIN] Данные сохранены в Redis")
                                        
                                        # Проверяем, что данные сохранились правильно
                                        logger.info(f"[ADMIN] Проверяем сохраненные данные в Redis")
                                        saved_state = redis_client.get(state_key)
                                        saved_data_raw = redis_client.get(data_key)
                                        
                                        logger.info(f"[ADMIN] Сохраненное состояние: {saved_state}")
                                        logger.info(f"[ADMIN] Сохраненные данные (raw, первые 500 символов): {saved_data_raw[:500] if saved_data_raw else 'None'}...")
                                        
                                        if saved_data_raw:
                                            saved_data = json.loads(saved_data_raw)
                                            logger.info(f"[ADMIN] Проверка сохраненных данных:")
                                            logger.info(f"[ADMIN]   - touch_content_id: {saved_data.get('touch_content_id')}")
                                            logger.info(f"[ADMIN]   - questions_list: список из {len(saved_data.get('questions_list', []))} элементов")
                                            logger.info(f"[ADMIN]   - current_question_index: {saved_data.get('current_question_index')}")
                                            logger.info(f"[ADMIN]   - answers: список из {len(saved_data.get('answers', []))} элементов")
                                            
                                            # Проверяем каждый вопрос в сохраненных данных
                                            saved_questions = saved_data.get('questions_list', [])
                                            logger.info(f"[ADMIN] Детали сохраненных вопросов:")
                                            for idx, question in enumerate(saved_questions):
                                                logger.info(f"[ADMIN]   Вопрос #{idx + 1}: длина={len(question)}, первые 100 символов: {question[:100]}...")
                                            
                                            # Сравниваем с исходным списком
                                            if len(saved_questions) == len(questions_list):
                                                logger.info(f"[ADMIN] ✓ Количество вопросов совпадает: {len(saved_questions)}")
                                            else:
                                                logger.error(f"[ADMIN] ✗ ОШИБКА: Количество вопросов не совпадает! Сохранено: {len(saved_questions)}, ожидалось: {len(questions_list)}")
                                            
                                            if saved_data.get('current_question_index') == 0:
                                                logger.info(f"[ADMIN] ✓ Индекс вопроса корректен: {saved_data.get('current_question_index')}")
                                            else:
                                                logger.error(f"[ADMIN] ✗ ОШИБКА: Индекс вопроса некорректен! Сохранено: {saved_data.get('current_question_index')}, ожидалось: 0")
                                        else:
                                            logger.error(f"[ADMIN] ✗ ОШИБКА: Данные не найдены в Redis по ключу {data_key}")
                                        
                                        logger.info(f"[ADMIN] ===== СОЗДАНИЕ СПИСКА ВОПРОСОВ ЗАВЕРШЕНО =====")
                                    else:
                                        logger.warning(f"[ADMIN] ✗ Список вопросов пуст после разделения")
                                        logger.warning(f"[ADMIN] Исходный текст вопросов был: {questions_text[:200]}...")
                                        logger.warning(f"[ADMIN] ===== СОЗДАНИЕ СПИСКА ВОПРОСОВ ЗАВЕРШЕНО С ПРЕДУПРЕЖДЕНИЕМ =====")
                            
                            sent_count += 1
                        except Exception as exc:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(
                                "Не удалось отправить касание пользователю %s: %s",
                                telegram_id,
                                exc,
                            )
                    
                    return sent_count
                finally:
                    await bot.session.close()
            
            sent_count = asyncio.run(run_send())
            self.message_user(
                request,
                f"Касание '{touch_content.title}' отправлено {sent_count} пользователям",
                messages.SUCCESS
            )
        except Exception as e:
            import traceback
            self.message_user(
                request,
                f"Ошибка при отправке касания: {str(e)}\n{traceback.format_exc()}",
                messages.ERROR
            )
    
    send_touch_to_all_users.short_description = "📤 Отправить касание всем пользователям"
