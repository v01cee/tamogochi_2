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

from datetime import date
from core.config import settings
from core.keyboards import KeyboardOperations
from core.states import NotificationSettingsStates, SaturdayReflectionStates
from core.texts import get_booking_text
from qwen_client import generate_qwen_response
from whisper_client import transcribe_audio
from io import BytesIO
from aiogram.types import CallbackQuery
from database.session import get_session
from repositories.saturday_reflection_repository import SaturdayReflectionRepository
from repositories.user_repository import UserRepository
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
    "Запустить курс в своей компании": "subscription_company_offer",
}

ABOUT_BUTTONS = {
    "<- Назад": "back_to_menu",
    "Познакомиться ближе": "know_better",
}

COMPANY_BUTTONS = {
    "Сайт компании": ("url", "https://happinessinaction.ru/"),
    "Telegram-канал Филиппа": ("url", "https://t.me/guzenuk"),
    "👉 Переход в ВК": "link_vk",
    "Продолжить": "continue_after_company",
}

VIDEO_BUTTONS = {
    "👉Смотреть видео": "watch_video",
    "Продолжить": "continue_after_video_intro",
}

PAYMENT_BUTTONS = {
    "Оплатить подписку на 30 дней": "payment",
    "Попробовать 7 дней бесплатно": "more_details",
}

SUBSCRIPTION_BUTTONS = {
    "Назад": "back_to_menu",
    "Оплатить подписку": "payment",
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
        "Настроить свое время": "notification_customize",
        "Настройки по умолчанию": "notification_use_default",
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
async def callback_my_subscription(callback: CallbackQuery, state: FSMContext):
    """Информация о подписке и действия."""
    # Сохраняем контекст, откуда пришли, чтобы можно было вернуться из оплаты
    await state.update_data(payment_source_context="my_subscription")
    
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


@router.callback_query(F.data == "subscription_company_offer")
async def callback_subscription_company_offer(callback: CallbackQuery):
    """Обработчик кнопки 'Запустить курс в своей компании'."""
    await _send_keyboard_message(
        callback,
        get_booking_text("subscription_company_offer"),
        {"<- Назад": "back_to_menu"},
        interval=1,
    )
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
    # Отвечаем на callback query сразу, чтобы избежать таймаута
    await callback.answer()
    
    session_gen = get_session()
    session = next(session_gen)
    try:
        try:
            user_repo = UserRepository(session)
            user = user_repo.get_by_telegram_id(callback.from_user.id)
        except Exception as db_error:
            # Если БД недоступна, продолжаем работу без сохранения
            logger.warning(f"Не удалось получить пользователя из БД: {db_error}. Продолжаем работу.")
            await callback.message.answer("База данных временно недоступна. Попробуйте позже.")
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
            return

        # Если не первый раз - показываем тот же контент «Стратегии дня», что и в дневном касании
        tz = ZoneInfo("Europe/Moscow")
        today = datetime.now(tz=tz).date()

        logger.info(
            "[DAY_STRATEGY] Пользователь %s: рассчитываем день курса для даты %s",
            callback.from_user.id,
            today,
        )

        course_day = calculate_course_day(user, today)
        touch_repo = TouchContentRepository(session)

        # Будем отправлять три касания: утро, день, вечер — как в реальных рассылках
        touch_order = [
            ("morning", "Касание УТРО"),
            ("day", "Касание ДЕНЬ"),
            ("evening", "Касание ВЕЧЕР"),
        ]

        # Базовая директория для видеофайлов касаний (Django складывает их в admin_panel/media)
        from pathlib import Path

        media_base = Path("admin_panel") / "media"

        any_content_sent = False

        for touch_type, header in touch_order:
            content = fetch_touch_content(touch_repo, touch_type=touch_type, course_day=course_day)
            if not content:
                # Если на конкретный день нет — используем дефолт или любой активный
                content = touch_repo.get_default(touch_type) or touch_repo.get_any_active(touch_type)

            if not content:
                logger.warning(
                    "[DAY_STRATEGY] Контент не найден для touch_type=%s, day=%s",
                    touch_type,
                    course_day,
                )
                continue

            any_content_sent = True

            logger.info(
                "[DAY_STRATEGY] Отправляем %s: id=%s, summary=%s, video_url=%s, video_file=%s",
                touch_type,
                content.id,
                "есть" if content.summary else "нет",
                "есть" if content.video_url else "нет",
                getattr(content, "video_file_path", None),
            )

            # Заголовок касания (как в скрине «Касание ДЕНЬ»)
            await callback.message.answer(header)
            await asyncio.sleep(3)

            # 1) summary используем как caption к видео, если оно есть
            caption = content.summary.strip() if content.summary else None

            # 2) видео / ссылка на видео
            video_file_path = getattr(content, "video_file_path", None)
            if video_file_path:
                from aiogram.types import FSInputFile

                file_path = media_base / video_file_path
                logger.info(
                    "[DAY_STRATEGY] Видео-файл для %s: %s (exists=%s)",
                    touch_type,
                    file_path,
                    file_path.exists(),
                )
                if file_path.exists():
                    try:
                        await callback.message.answer_video(
                            FSInputFile(file_path),
                            caption=caption,
                        )
                    except Exception as send_err:  # noqa: BLE001
                        logger.warning("Не удалось отправить видео-файл %s: %s", file_path, send_err)
                        if content.video_url:
                            await callback.message.answer(content.video_url.strip())
                            if caption:
                                await asyncio.sleep(3)
                                await callback.message.answer(caption)
                elif content.video_url:
                    await callback.message.answer(content.video_url.strip())
                    if caption:
                        await asyncio.sleep(3)
                        await callback.message.answer(caption)
            elif content.video_url:
                # Видео по ссылке + caption отдельным сообщением
                await callback.message.answer(content.video_url.strip())
                if caption:
                    await asyncio.sleep(3)
                    await callback.message.answer(caption)
            else:
                # Если видео нет совсем — просто отправляем описание
                if caption:
                    await callback.message.answer(caption)

            # 3) вопросы (если есть): сначала короткое вступление, затем список вопросов
            if content.questions:
                await asyncio.sleep(3)
                await callback.message.answer("Какие вопросы Вас сегодня ожидают.")
                await asyncio.sleep(3)
                await callback.message.answer(content.questions.strip())

            # Пауза перед следующим типом касания
            await asyncio.sleep(3)

        if not any_content_sent:
            # Если ничего вообще не нашли по всем типам касаний
            logger.warning("[DAY_STRATEGY] Контент для стратегии дня не найден (morning/day/evening)")
            error_message = "Контент для стратегии дня временно недоступен. Пожалуйста, попробуйте позже."
            await callback.message.answer(error_message)

            step_6_text = get_booking_text("step_6")
            await _send_keyboard_message(
                callback,
                step_6_text,
                MAIN_MENU_BUTTONS,
                interval=2,
            )

    finally:
        session.close()


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
    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    author_text = get_booking_text("author_info")
    await callback.message.answer(author_text)

    company_text = get_booking_text("company_info")
    await _send_keyboard_message(
        callback,
        company_text,
        COMPANY_BUTTONS,
        interval=1,
    )


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
async def callback_continue_after_video_intro(callback: CallbackQuery, state: FSMContext):
    """Экран после введения в курс."""
    # Сохраняем контекст, откуда пришли, чтобы можно было вернуться из оплаты
    await state.update_data(payment_source_context="after_video")
    
    await _send_keyboard_message(
        callback,
        get_booking_text("after_video"),
        PAYMENT_BUTTONS,
        interval=2,
    )
    await callback.answer()


@router.callback_query(F.data == "payment")
async def callback_payment(callback: CallbackQuery, state: FSMContext):
    """Генерация ссылки на оплату через Robokassa."""
    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    # Сохраняем текущее состояние и данные для возможности вернуться назад
    current_state = await state.get_state()
    current_data = await state.get_data()
    
    # Сохраняем информацию о том, откуда пришли на оплату
    # Проверяем, есть ли сохраненный контекст (устанавливается перед переходом на оплату)
    payment_context = current_data.get("payment_source_context")
    
    # Если контекст еще не сохранен, определяем его на основе состояния
    if not payment_context:
        if current_state and "ProfileStates" in str(current_state):
            payment_context = "subscription_choice"
        else:
            # По умолчанию считаем, что пришли из after_video
            payment_context = "after_video"
    
    # Сохраняем полную информацию о предыдущем месте
    await state.update_data(
        payment_previous_state=str(current_state) if current_state else None,
        payment_previous_data=current_data.copy() if current_data else {},
        payment_context=payment_context
    )
    
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

        # Сначала отправляем сообщение о том, что ссылка готова
        await callback.message.answer(get_booking_text("payment_created"))
        
        # Затем отправляем сообщение с предложением оплаты и кнопками
        buttons = {
            "Оплатить 5 990 ₽": ("url", payment.payment_url or ""),
            "<- Назад": "payment_back",
        }
        keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=1)
        await callback.message.answer(get_booking_text("payment_offer"), reply_markup=keyboard)
    except Exception as exc:
        logger.exception("Не удалось создать ссылку на оплату: %s", exc)
        await callback.message.answer(get_booking_text("payment_error"))
    finally:
        session.close()

    await callback.answer()


@router.callback_query(F.data == "payment_back")
async def callback_payment_back(callback: CallbackQuery, state: FSMContext):
    """Возврат назад из оплаты к предыдущему экрану."""
    data = await state.get_data()
    previous_context = data.get("payment_context")
    previous_state_str = data.get("payment_previous_state")
    previous_data = data.get("payment_previous_data", {})
    
    await callback.answer()
    
    # Восстанавливаем данные в state (кроме временных данных об оплате)
    if previous_data:
        # Сохраняем контекст источника для будущего возврата
        payment_source = previous_data.get("payment_source_context")
        
        # Восстанавливаем все данные кроме временных данных об оплате
        for key, value in previous_data.items():
            if key not in ["payment_context", "payment_previous_state", "payment_previous_data"]:
                await state.update_data(**{key: value})
        
        # Восстанавливаем контекст источника
        if payment_source:
            await state.update_data(payment_source_context=payment_source)
    
    # Очищаем временные данные оплаты
    await state.update_data(
        payment_context=None,
        payment_previous_state=None,
        payment_previous_data=None
    )
    
    # Возвращаемся на экран, откуда пришли
    if previous_context == "subscription_choice":
        # Показываем экран выбора подписки
        subscription_text = get_booking_text("subscription_choice")
        subscription_keyboard = await keyboard_ops.create_keyboard(
            buttons={
                "Бесплатная неделя": "free_week",
                "Подписка на месяц": "monthly_subscription",
            },
            interval=2,
        )
        await callback.message.answer(subscription_text, reply_markup=subscription_keyboard)
    elif previous_context == "after_video":
        # Возвращаемся к экрану после видео
        await _send_keyboard_message(
            callback,
            get_booking_text("after_video"),
            PAYMENT_BUTTONS,
            interval=2,
        )
    else:
        # По умолчанию возвращаемся в меню подписки
        await callback_my_subscription(callback)


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

    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")

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
    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    await state.clear()
    await _send_keyboard_message(
        callback,
        get_booking_text("step_6"),
        MAIN_MENU_BUTTONS,
        interval=2,
    )


@router.callback_query(F.data == "saturday_reflection_start")
async def callback_saturday_reflection_start(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Начать' для стратсубботы - начало рефлексии по 5 сегментам."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[SATURDAY] Кнопка 'Начать' нажата пользователем {callback.from_user.id}")
    
    # Сразу отвечаем на callback, чтобы не истек таймаут
    try:
        await callback.answer()
    except Exception as e:
        logger.warning(f"[SATURDAY] Не удалось ответить на callback: {e}")
        # Продолжаем выполнение даже если ответ не удался
    
    # Инициализируем данные для рефлексии
    await state.update_data(
        saturday_segment=1,
        saturday_answers={}
    )
    
    # Отправляем первый вопрос рефлексии (1/5)
    first_question = (
        "1/5 Первый шаг — похвастаться 🌟\n"
        "Какие победы случились у тебя на этой неделе в главных направлениях? Что удалось сделать, какие открытия или находки тебя поразили, что получилось особенно классно?\n\n"
        "✍️ Напиши или наговори свой ответ. Мы сохраним его в твою карту личной стратегии"
    )
    
    try:
        # Добавляем кнопки "Написать" и "Назад"
        saturday_keyboard = await keyboard_ops.create_keyboard(
            buttons={
                "Написать": "saturday_show_question_1",
                "<- Назад": "back_to_menu",
            },
            interval=2,
        )
        await callback.message.answer(first_question, reply_markup=saturday_keyboard)
        await state.set_state(SaturdayReflectionStates.answering_segment_1)
        
        # Проверяем, что состояние установлено
        current_state = await state.get_state()
        logger.info(f"[SATURDAY] Состояние установлено: {current_state}")
    except Exception as e:
        logger.error(f"[SATURDAY] Ошибка при отправке сообщения или установке состояния: {e}", exc_info=True)
        # Пытаемся отправить сообщение об ошибке
        try:
            await callback.message.answer("Произошла ошибка. Попробуйте нажать кнопку 'Начать' еще раз.")
        except:
            pass


async def _handle_saturday_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
    segment: int,
    is_confirmed: bool
) -> None:
    """Обработать подтверждение или редактирование ответа на сегмент рефлексии."""
    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except:
        pass
    
    data = await state.get_data()
    processed_text = data.get("temp_processed_text", "")
    next_question = data.get("temp_next_question", "")
    
    if is_confirmed:
        # Сохраняем ответ
        answers = data.get("saturday_answers", {})
        answers[f"segment_{segment}"] = processed_text
        await state.update_data(saturday_answers=answers)
        
        # Сохраняем в БД
        try:
            session = next(get_session())
            try:
                user_repo = UserRepository(session)
                user = user_repo.get_by_telegram_id(callback.from_user.id)
                
                if user:
                    reflection_repo = SaturdayReflectionRepository(session)
                    reflection_date = date.today()
                    
                    # Сохраняем текущий сегмент
                    kwargs = {f"segment_{segment}": processed_text}
                    reflection_repo.create_or_update(
                        user_id=user.id,
                        reflection_date=reflection_date,
                        **kwargs
                    )
                    logger.info(f"[SATURDAY] Сохранен сегмент {segment} для пользователя {user.id}")
            finally:
                session.close()
        except Exception as e:
            logger.error(f"[SATURDAY] Ошибка при сохранении в БД: {e}", exc_info=True)
        
        # Отправляем подтверждение
        await callback.message.answer("✅ Спасибо! Ваш ответ сохранён.")
        
        # Если это не последний сегмент, отправляем следующий вопрос
        if segment < 5:
            # Определяем следующее состояние
            next_states = {
                1: SaturdayReflectionStates.answering_segment_2,
                2: SaturdayReflectionStates.answering_segment_3,
                3: SaturdayReflectionStates.answering_segment_4,
                4: SaturdayReflectionStates.answering_segment_5,
            }
            next_state = next_states.get(segment)
            if next_state and next_question:
                # Добавляем кнопки "Написать" и "Назад"
                next_segment = segment + 1
                saturday_keyboard = await keyboard_ops.create_keyboard(
                    buttons={
                        "Написать": f"saturday_show_question_{next_segment}",
                        "<- Назад": "back_to_menu",
                    },
                    interval=2,
                )
                await callback.message.answer(next_question, reply_markup=saturday_keyboard)
                await state.set_state(next_state)
        else:
            # Все сегменты пройдены - сохраняем все ответы в БД
            try:
                session = next(get_session())
                try:
                    user_repo = UserRepository(session)
                    user = user_repo.get_by_telegram_id(callback.from_user.id)
                    
                    if user:
                        reflection_repo = SaturdayReflectionRepository(session)
                        reflection_date = date.today()
                        
                        # Сохраняем все ответы
                        reflection_repo.create_or_update(
                            user_id=user.id,
                            reflection_date=reflection_date,
                            segment_1=answers.get("segment_1"),
                            segment_2=answers.get("segment_2"),
                            segment_3=answers.get("segment_3"),
                            segment_4=answers.get("segment_4"),
                            segment_5=answers.get("segment_5"),
                        )
                        logger.info(f"[SATURDAY] Сохранена полная рефлексия для пользователя {user.id}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"[SATURDAY] Ошибка при сохранении полной рефлексии в БД: {e}", exc_info=True)
            
            await callback.message.answer("🎉 Отлично! Вы завершили рефлексию стратсубботы. Все ваши ответы сохранены в карту личной стратегии.")
            await state.clear()
    else:
        # Пользователь хочет изменить ответ - возвращаемся к вводу
        answering_states = {
            1: SaturdayReflectionStates.answering_segment_1,
            2: SaturdayReflectionStates.answering_segment_2,
            3: SaturdayReflectionStates.answering_segment_3,
            4: SaturdayReflectionStates.answering_segment_4,
            5: SaturdayReflectionStates.answering_segment_5,
        }
        # Добавляем кнопки "Написать" и "Назад"
        saturday_keyboard = await keyboard_ops.create_keyboard(
            buttons={
                "Написать": f"saturday_show_question_{segment}",
                "<- Назад": "back_to_menu",
            },
            interval=2,
        )
        await callback.message.answer("Хорошо, отправьте ваш ответ заново.", reply_markup=saturday_keyboard)
        await state.set_state(answering_states[segment])


@router.callback_query(F.data.startswith("saturday_confirm_"))
async def callback_saturday_confirm(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Все верно' для подтверждения ответа."""
    segment = int(callback.data.split("_")[-1])
    await _handle_saturday_confirmation(callback, state, segment, is_confirmed=True)


@router.callback_query(F.data.startswith("saturday_edit_"))
async def callback_saturday_edit(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить' для редактирования ответа."""
    segment = int(callback.data.split("_")[-1])
    await _handle_saturday_confirmation(callback, state, segment, is_confirmed=False)


@router.callback_query(F.data.startswith("saturday_show_question_"))
async def callback_saturday_show_question(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Написать' - показывает вопрос текущего сегмента."""
    await callback.answer()
    
    segment = int(callback.data.split("_")[-1])
    
    # Вопросы для каждого сегмента
    questions = {
        1: (
            "1/5 Первый шаг — похвастаться 🌟\n"
            "Какие победы случились у тебя на этой неделе в главных направлениях? Что удалось сделать, какие открытия или находки тебя поразили, что получилось особенно классно?\n\n"
            "✍️ Напиши или наговори свой ответ. Мы сохраним его в твою карту личной стратегии"
        ),
        2: (
            "Второй шаг — посмотреть на то, что не получилось.\n"
            "Где ты застрял? В чём было ключевое противоречие недели? Какие ограничения встретились, что забирало энергию?\n"
            "Важно не просто пожаловаться, а конструктивно разобрать, где были сложности.\n"
            "✍️ Напиши или наговори свои наблюдения — мы добавим их в твою карту личной стратегии"
        ),
        3: (
            "Третий шаг — поблагодарить 🙏\n"
            "Вспомни, кто помог тебе на этой неделе. Чья поддержка была особенно ценной? Кому хочется сказать спасибо?\n"
            "Для продвинутых: прямо сейчас можно взять телефон и отправить пару тёплых слов тем, о ком ты подумал. Благодарность — это практика, которая расширяет поле возможностей.\n"
            "✍️ Запиши или напиши свой ответ — он тоже войдёт в твою стратегию"
        ),
        4: (
            "Четвёртый шаг — помечтать ✨\n"
            "Вернись к большим целям и намерениям, которые ставил(а) в начале. Подумай: что из опыта этой недели хочется добавить в них? Какие новые инсайты и наблюдения стоит приземлить в твою личную стратегию?\n"
            "✍️ Поделись своими мыслями письменно или голосом"
        ),
        5: (
            "И пятый шаг — пообещать 💪\n"
            "Выбери один-два фокуса на следующую неделю. Это должны быть те самые «сдвиговые задачи», которые реально продвинут тебя к важным целям.\n"
            "✍️ Напиши или наговори, что берёшь в фокус. Мы сохраним это в твоей карте стратегии как твой следующий шаг"
        ),
    }
    
    question = questions.get(segment)
    if not question:
        await callback.message.answer("Ошибка: не найден вопрос для этого сегмента.")
        return
    
    # Определяем состояния для каждого сегмента
    answering_states = {
        1: SaturdayReflectionStates.answering_segment_1,
        2: SaturdayReflectionStates.answering_segment_2,
        3: SaturdayReflectionStates.answering_segment_3,
        4: SaturdayReflectionStates.answering_segment_4,
        5: SaturdayReflectionStates.answering_segment_5,
    }
    
    # Добавляем кнопки "Написать" и "Назад"
    saturday_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Написать": f"saturday_show_question_{segment}",
            "<- Назад": "back_to_menu",
        },
        interval=2,
    )
    
    await callback.message.answer(question, reply_markup=saturday_keyboard)
    await state.set_state(answering_states[segment])


