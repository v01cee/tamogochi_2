import asyncio
import json
import logging
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from typing import TYPE_CHECKING

import redis

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile

from core.config import settings
from core.keyboards import KeyboardOperations
from core.states import NotificationSettingsStates
from core.texts import get_booking_text
from database.session import get_session
from repositories.touch_content_repository import TouchContentRepository
from repositories.user_repository import UserRepository
from services.payment import PaymentService
from services.touch_utils import calculate_course_day, fetch_touch_content

if TYPE_CHECKING:
    from models.user import User

router = Router()
keyboard_ops = KeyboardOperations()
logger = logging.getLogger(__name__)


@router.callback_query.middleware()
async def log_callback_queries(handler, event: CallbackQuery, data: dict):
    """Middleware для логирования всех callback queries"""
    logger.info(
        f"[CALLBACK] Пользователь {event.from_user.id} (@{event.from_user.username}) "
        f"нажал кнопку: {event.data}"
    )
    return await handler(event, data)

MAIN_MENU_BUTTONS = {
    "Обратная связь": "feedback",
    "О боте": "about_bot",
    "Стратегия дня": "day_strategy",
    "Настройка бота": "bot_settings",
    "Моя подписка": "my_subscription",
}

ABOUT_BUTTONS = {
    "<- Назад": "back_to_menu",
    "Познакомиться ближе": "know_better",
}

COMPANY_BUTTONS = {
    "👉 Переход в ТГ": "link_telegram",
    "👉 Переход в ВК": "link_vk",
    "Продолжить": "continue_after_company",
}

VIDEO_BUTTONS = {
    "👉 Посмотреть видео": "watch_video",
    "Продолжить": "continue_after_video_intro",
}

PAYMENT_BUTTONS = {
    "Оплата": "payment",
    "Подробнее": "more_details",
}

SUBSCRIPTION_BUTTONS = {
    "Назад": "back_to_menu",
    "Оплатить подписку": "payment",
    "Познакомиться поближе": "know_better",
}

NOTIFICATION_ENTRY_BUTTONS = {
    "Главное меню": "back_to_menu",
    "Продолжить": "notification_use_default",
}

NOTIFICATION_TOUCH_BUTTONS = {
    "🌅 Утро": "notification_touch_morning",
    "🌞 День": "notification_touch_day",
    "🌙 Вечер": "notification_touch_evening",
    "Назад": "notification_back_to_entry",
}

NOTIFICATION_AFTER_SAVE_BUTTONS = {
    "Настроить ещё": "notification_customize",
    "В главное меню": "back_to_menu",
}

DEFAULT_NOTIFICATION_TIMES = {
    "morning": time(hour=9, minute=0),
    "day": time(hour=12, minute=0),
    "evening": time(hour=21, minute=0),
}


async def _send_keyboard_message(
    callback: CallbackQuery,
    text: str,
    buttons: dict[str, str],
    *,
    interval: int,
) -> None:
    keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=interval)
    await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Хендлер справочного сообщения."""
    text = get_booking_text("help")
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "info")
async def callback_info(callback: CallbackQuery):
    """Хендлер информационного сообщения."""
    text = "Информация о боте"
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "course_start")
async def callback_course_start(callback: CallbackQuery):
    """Начало курса после нажатия кнопки 'Старт'."""
    # Проверяем, первый ли визит пользователя
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_by_telegram_id(callback.from_user.id)
        
        # Если пользователь не первый раз, сразу показываем главное меню
        if user and not user.is_first_visit:
            step_6_text = get_booking_text("step_6")
            await _send_keyboard_message(
                callback,
                step_6_text,
                MAIN_MENU_BUTTONS,
                interval=2,
            )
            await callback.answer()
            return
    finally:
        session.close()
    
    # Если первый визит, показываем вводные сообщения
    text = get_booking_text("step_3")
    await callback.message.answer(text)

    step_4_text = get_booking_text("step_4")
    await callback.message.answer(step_4_text)

    step_5_text = get_booking_text("step_5")
    yes_keyboard = await keyboard_ops.create_keyboard(
        buttons={"Да, интересно!": "yes_interested"},
        interval=1,
    )
    await callback.message.answer(step_5_text, reply_markup=yes_keyboard)
    await callback.answer()


@router.callback_query(F.data == "yes_interested")
async def callback_yes_interested(callback: CallbackQuery):
    """Показ главного меню после согласия продолжить."""
    step_6_text = get_booking_text("step_6")
    await _send_keyboard_message(
        callback,
        step_6_text,
        MAIN_MENU_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "bot_settings")
async def callback_bot_settings(callback: CallbackQuery, state: FSMContext):
    """Настройка бота: показ настроек уведомлений или вводных сообщений для первого визита."""
    session_gen = get_session()
    session = next(session_gen)
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            user = user_repo.create(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                language_code=callback.from_user.language_code,
            )

        # Если первый визит, показываем вводные сообщения вместо настроек
        if user.is_first_visit:
            await callback.answer()
            # Показываем первое сообщение о процессе курса (7.4)
            first_text = get_booking_text("know_better_first_time")
            await callback.message.answer(first_text)

            # Показываем описание трех касаний (7.5) с кнопкой "Понятно, идем дальше"
            second_text = get_booking_text("know_better_three_touches")
            await _send_keyboard_message(
                callback,
                second_text,
                {"Понятно, идем дальше": "understood_move_on"},
                interval=1,
            )
            return
    finally:
        session.close()

    # Если не первый визит, показываем настройки уведомлений
    await state.clear()
    await state.set_state(NotificationSettingsStates.choosing_touch)
    
    # Кнопки для настройки уведомлений
    notification_setup_buttons = {
        "Настроить под себя": "notification_customize",
        "Дефолтные настройки": "notification_use_default",
        "Назад": "back_to_menu",
    }
    
    await _send_keyboard_message(
        callback,
        get_booking_text("notification_intro"),
        notification_setup_buttons,
        interval=1,
    )
    await callback.answer()


@router.callback_query(F.data == "my_subscription")
async def callback_my_subscription(callback: CallbackQuery):
    """Информация о подписке и действия."""
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            language_code=callback.from_user.language_code,
        )
        trial_status, subscription_status = _build_subscription_status(user)
    finally:
        session.close()

    text = get_booking_text("subscription_overview").format(
        trial_status=trial_status,
        subscription_status=subscription_status,
    )
    keyboard = await keyboard_ops.create_keyboard(SUBSCRIPTION_BUTTONS, interval=1)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "about_bot")
async def callback_about_bot(callback: CallbackQuery):
    """Экран 'О боте'."""
    await _send_keyboard_message(
        callback,
        get_booking_text("about_bot"),
        ABOUT_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "day_strategy")
async def callback_day_strategy(callback: CallbackQuery):
    """Экран 'Стратегия дня'."""
    session_gen = get_session()
    session = next(session_gen)
    try:
        try:
            user_repo = UserRepository(session)
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        except Exception as db_error:
            # Если БД недоступна, продолжаем работу без сохранения
            logger.warning(f"Не удалось получить пользователя из БД: {db_error}. Продолжаем работу.")
            await callback.answer("База данных временно недоступна. Попробуйте позже.")
            return

        if not user:
            user = user_repo.create(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name,
                language_code=callback.from_user.language_code,
            )

        # Если первый раз - показываем интро
        if user.is_first_visit:
            first_text = get_booking_text("know_better_first_time")
            await callback.message.answer(first_text)

            second_text = get_booking_text("know_better_three_touches")
            await _send_keyboard_message(
                callback,
                second_text,
                {"Понятно, идем дальше": "understood_move_on"},
                interval=1,
            )
            await callback.answer()
            return

        # Если не первый раз - показываем все контенты для дня 1 (тестово)
        test_course_day = 1  # Тестово используем день 1
        
        logger.info(f"[DAY_STRATEGY] Пользователь {callback.from_user.id}: отправляем контент для дня {test_course_day}")
        
        touch_repo = TouchContentRepository(session)
        
        # Получаем все три типа касаний для дня 1
        touch_types = ["morning", "day", "evening"]
        touch_labels = {"morning": "🌅 Утро", "day": "🌞 День", "evening": "🌙 Вечер"}
        
        any_content_found = False
        
        # Отправляем контент для каждого типа касания
        for touch_type in touch_types:
            content = touch_repo.get_for_day(touch_type, test_course_day)
            if not content:
                # Если нет контента для конкретного дня, пробуем дефолтный
                content = touch_repo.get_default(touch_type)
            
            if content:
                any_content_found = True
                logger.info(f"[DAY_STRATEGY] Отправляем {touch_type}: id={content.id}, summary={'есть' if content.summary else 'нет'}, video_url={'есть' if content.video_url else 'нет'}, questions={'есть' if content.questions else 'нет'}")
                
                # Отправляем заголовок типа касания
                await callback.message.answer(f"{touch_labels.get(touch_type, touch_type.capitalize())}")
                
                # Шаг 1: Отправляем описание (summary) - если есть
                if content.summary:
                    summary_text = content.summary.strip()
                    await callback.message.answer(summary_text)
                
                # Шаг 2: Отправляем ссылку на видео - если есть
                if content.video_url:
                    video_url = content.video_url.strip()
                    await callback.message.answer(video_url)
                
                # Шаг 3: Отправляем вопросы - если есть (одним сообщением)
                if content.questions:
                    questions_text = content.questions.strip()
                    # Отправляем все вопросы одним сообщением
                    await callback.message.answer(questions_text)
                
                # Добавляем небольшую паузу между типами касаний
                await asyncio.sleep(0.5)
        
        # Отправляем финальное сообщение
        if any_content_found:
            final_message = "Вот такой план на сегодня"
            back_keyboard = await keyboard_ops.create_keyboard(
                buttons={"Назад": "back_to_menu"},
                interval=1
            )
            await callback.message.answer(final_message, reply_markup=back_keyboard)
        else:
            # Если контента нет, показываем сообщение об ошибке
            logger.warning(f"[DAY_STRATEGY] Контент не найден для дня {test_course_day}")
            error_message = "Контент для стратегии дня временно недоступен. Пожалуйста, попробуйте позже."
            await callback.message.answer(error_message)
            
            # Показываем главное меню
            step_6_text = get_booking_text("step_6")
            await _send_keyboard_message(
                callback,
                step_6_text,
                MAIN_MENU_BUTTONS,
                interval=2,
            )

    finally:
        session.close()

    await callback.answer()


@router.callback_query(F.data == "know_better")
async def callback_know_better(callback: CallbackQuery):
    """Дублирует поведение 'Стратегии дня'."""
    await callback_day_strategy(callback)


@router.callback_query(F.data == "understood_move_on")
async def callback_understood_move_on(callback: CallbackQuery, state: FSMContext):
    """Экран настройки уведомлений."""
    await state.clear()
    await state.set_state(NotificationSettingsStates.choosing_touch)
    await _send_keyboard_message(
        callback,
        get_booking_text("notification_intro"),
        NOTIFICATION_ENTRY_BUTTONS,
        interval=1,
    )
    await callback.answer()


@router.callback_query(F.data == "continue_after_notification")
async def callback_continue_after_notification(callback: CallbackQuery):
    """Экран с информацией об авторе."""
    author_text = get_booking_text("author_info")
    await callback.message.answer(author_text)

    company_text = get_booking_text("company_info")
    await _send_keyboard_message(
        callback,
        company_text,
        COMPANY_BUTTONS,
        interval=1,
    )
    await callback.answer()


@router.callback_query(F.data == "link_telegram")
async def callback_link_telegram(callback: CallbackQuery):
    """Заглушка для ссылки на Telegram."""
    await callback.answer("Ссылка на Telegram канал будет добавлена позже")


@router.callback_query(F.data == "link_vk")
async def callback_link_vk(callback: CallbackQuery):
    """Заглушка для ссылки на VK."""
    await callback.answer("Ссылка на ВК будет добавлена позже")


@router.callback_query(F.data == "continue_after_company")
async def callback_continue_after_company(callback: CallbackQuery):
    """Экран с вводным видео курса."""
    await _send_keyboard_message(
        callback,
        get_booking_text("course_intro"),
        VIDEO_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "watch_video")
async def callback_watch_video(callback: CallbackQuery):
    """Заглушка для просмотра видео."""
    await callback.answer("Видео будет добавлено позже")


@router.callback_query(F.data == "continue_after_video_intro")
async def callback_continue_after_video_intro(callback: CallbackQuery):
    """Экран после введения в курс."""
    await _send_keyboard_message(
        callback,
        get_booking_text("after_video"),
        PAYMENT_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "payment")
async def callback_payment(callback: CallbackQuery):
    """Генерация ссылки на оплату через Robokassa."""
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            language_code=callback.from_user.language_code,
        )

        payment_service = PaymentService(session)
        amount = Decimal("5990.00")
        payment = payment_service.create_payment(
            user_id=user.id,
            amount=amount,
            description="Подписка на 4 недели курса",
        )

        buttons = {
            "Оплатить 5 990 ₽": ("url", payment.payment_url or ""),
            "Главное меню": "back_to_menu",
        }
        keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=1)

        await callback.message.answer(get_booking_text("payment_offer"), reply_markup=keyboard)
        await callback.message.answer(get_booking_text("payment_created"))
    except Exception as exc:
        logger.exception("Не удалось создать ссылку на оплату: %s", exc)
        await callback.message.answer(get_booking_text("payment_error"))
    finally:
        session.close()

    await callback.answer()


@router.callback_query(F.data == "notification_back_to_entry", NotificationSettingsStates.choosing_touch)
async def callback_notification_back_to_entry(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(NotificationSettingsStates.choosing_touch)
    await _send_keyboard_message(
        callback,
        get_booking_text("notification_intro"),
        NOTIFICATION_ENTRY_BUTTONS,
        interval=1,
    )
    await callback.answer()


@router.callback_query(F.data == "notification_customize", NotificationSettingsStates.choosing_touch)
async def callback_notification_customize(callback: CallbackQuery, state: FSMContext):
    await state.set_state(NotificationSettingsStates.choosing_touch)
    await _send_keyboard_message(
        callback,
        get_booking_text("notification_choose_touch"),
        NOTIFICATION_TOUCH_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "notification_use_default", NotificationSettingsStates.choosing_touch)
async def callback_notification_use_default(callback: CallbackQuery, state: FSMContext):
    session = next(get_session())
    try:
        repo = UserRepository(session)
        user = repo.get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            language_code=callback.from_user.language_code,
        )
        for touch, default_time in DEFAULT_NOTIFICATION_TIMES.items():
            repo.set_notification_time(user, touch, default_time)
        is_first_visit = user.is_first_visit
    finally:
        session.close()

    await state.clear()
    
    # Отправляем подтверждение
    default_info_text = get_booking_text("notification_default_info")
    
    # Для первого визита показываем "Продолжить", иначе "Назад"
    if is_first_visit:
        buttons = {"Продолжить": "continue_after_notification"}
    else:
        buttons = {"<- Назад": "back_to_menu"}
    
    keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=1)
    await callback.message.answer(default_info_text, reply_markup=keyboard)
    await callback.answer()


async def _start_waiting_time(
    callback: CallbackQuery,
    state: FSMContext,
    touch_type: str,
    label: str,
) -> None:
    await state.update_data(selected_touch=touch_type, touch_label=label)
    await state.set_state(NotificationSettingsStates.waiting_for_time)
    await callback.message.answer(get_booking_text("notification_time_prompt"))
    await callback.answer()


@router.callback_query(F.data == "notification_touch_morning", NotificationSettingsStates.choosing_touch)
async def callback_notification_touch_morning(callback: CallbackQuery, state: FSMContext):
    await _start_waiting_time(callback, state, "morning", "утром")


@router.callback_query(F.data == "notification_touch_day", NotificationSettingsStates.choosing_touch)
async def callback_notification_touch_day(callback: CallbackQuery, state: FSMContext):
    await _start_waiting_time(callback, state, "day", "днём")


@router.callback_query(F.data == "notification_touch_evening", NotificationSettingsStates.choosing_touch)
async def callback_notification_touch_evening(callback: CallbackQuery, state: FSMContext):
    await _start_waiting_time(callback, state, "evening", "вечером")


def parse_notification_time(text: str) -> time | None:
    if not text:
        return None
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", text)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        return None
    return time(hour=hours, minute=minutes)


def _build_subscription_status(user: "User") -> tuple[str, str]:
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)

    trial_status = "не использована"

    if user.subscription_type == "free_week":
        if user.subscription_started_at:
            start = user.subscription_started_at.astimezone(tz)
            end = start + timedelta(days=7)
            if end <= now:
                trial_status = "использована"
            else:
                days_left = max(0, (end - now).days)
                trial_status = f"активна, осталось {days_left} дн."
        else:
            trial_status = "не использована"
    elif user.subscription_started_at:
        trial_status = "использована"

    subscription_status = "не оплачена"
    if user.subscription_paid_at:
        paid_start = user.subscription_paid_at.astimezone(tz)
        paid_until = paid_start + timedelta(weeks=4)
        subscription_status = paid_until.strftime("%d.%m.%Y")

    return trial_status, subscription_status


@router.callback_query(F.data == "chat_placeholder")
async def callback_chat_placeholder(callback: CallbackQuery):
    """Обработчик заглушки для кнопки 'Перейти в чат'"""
    await callback.answer("Чат пока не доступен. Скоро мы его добавим! 👋", show_alert=False)


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню и очистка состояния."""
    await state.clear()
    await _send_keyboard_message(
        callback,
        get_booking_text("step_6"),
        MAIN_MENU_BUTTONS,
        interval=2,
    )
    await callback.answer()


