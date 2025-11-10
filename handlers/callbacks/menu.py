from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards import KeyboardOperations
from core.texts import get_booking_text

router = Router()
keyboard_ops = KeyboardOperations()

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

NOTIFICATION_BUTTONS = {
    "Главное меню": "back_to_menu",
    "Продолжить": "continue_after_notification",
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
async def callback_bot_settings(callback: CallbackQuery):
    """Заглушка для настройки бота."""
    await callback.message.answer("Настройка бота")
    await callback.answer()


@router.callback_query(F.data == "my_subscription")
async def callback_my_subscription(callback: CallbackQuery):
    """Заглушка раздела подписки."""
    await callback.message.answer("Моя подписка")
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


@router.callback_query(F.data == "know_better")
async def callback_know_better(callback: CallbackQuery):
    """Дублирует поведение 'Стратегии дня'."""
    await callback_day_strategy(callback)


@router.callback_query(F.data == "understood_move_on")
async def callback_understood_move_on(callback: CallbackQuery):
    """Экран настройки уведомлений."""
    await _send_keyboard_message(
        callback,
        get_booking_text("notification_setup"),
        NOTIFICATION_BUTTONS,
        interval=2,
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
    """Заглушка экрана оплаты."""
    await callback.answer("Оплата будет добавлена позже")


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


