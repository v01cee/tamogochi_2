from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards import KeyboardOperations
from core.states import ProfileStates
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


async def _send_main_menu(callback: CallbackQuery, state: FSMContext | None = None):
    """Показывает главное меню пользователю."""
    if state is not None:
        await state.clear()

    step_6_text = get_booking_text("step_6")
    menu_keyboard = await keyboard_ops.create_keyboard(
        buttons=MAIN_MENU_BUTTONS,
        interval=2,
    )
    await callback.message.answer(step_6_text, reply_markup=menu_keyboard)


@router.callback_query(F.data == "edit_profile_data")
async def callback_edit_profile_data(callback: CallbackQuery, state: FSMContext):
    """Выбор блока для редактирования вызовов/целей."""
    edit_text = get_booking_text("edit_question")
    edit_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Цели": "edit_goals",
            "Вызовы": "edit_challenges",
        },
        interval=2,
    )
    await callback.message.answer(edit_text, reply_markup=edit_keyboard)
    await callback.answer()


@router.callback_query(F.data == "edit_challenges")
async def callback_edit_challenges(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу вызовов."""
    text = get_booking_text("challenges_request")
    await callback.message.answer(text)
    await state.set_state(ProfileStates.waiting_for_challenges)
    await callback.answer()


@router.callback_query(F.data == "edit_goals")
async def callback_edit_goals(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу целей."""
    text = get_booking_text("goals_request")
    await callback.message.answer(text)
    await state.set_state(ProfileStates.waiting_for_goals)
    await callback.answer()


@router.callback_query(F.data == "confirm_profile_data")
async def callback_confirm_profile_data(callback: CallbackQuery, state: FSMContext):
    """Подтверждение блока с целями/вызовами и выбор подписки."""
    import logging
    logger = logging.getLogger(__name__)
    
    data = await state.get_data()
    goals = data.get("goals", "%N%")
    
    logger.info(f"[PROFILE] confirm_profile_data: goals value = '{goals}', type = {type(goals)}")

    # Если целей еще нет, переходим к запросу целей
    # Проверяем, что goals не установлен или равен маркеру отсутствия
    if not goals or goals == "%N%" or (isinstance(goals, str) and goals.strip() == ""):
        logger.info("[PROFILE] Goals not set, requesting goals")
        goals_text = get_booking_text("goals_request")
        await callback.message.answer(goals_text)
        await state.set_state(ProfileStates.waiting_for_goals)
        await callback.answer()
        return
    
    logger.info("[PROFILE] Goals already set, proceeding to subscription choice")

    # Если цели уже есть, переходим к выбору подписки
    # Сохраняем контекст, откуда пришли, чтобы можно было вернуться из оплаты
    await state.update_data(payment_source_context="subscription_choice")
    
    subscription_text = get_booking_text("subscription_choice")
    subscription_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Бесплатная неделя": "free_week",
            "Подписка на месяц": "monthly_subscription",
        },
        interval=2,
    )
    await callback.message.answer(subscription_text, reply_markup=subscription_keyboard)
    await callback.answer()


@router.callback_query(F.data == "consent_disagree")
async def callback_consent_disagree(callback: CallbackQuery, state: FSMContext):
    """Отказ от согласия на обработку персональных данных."""
    disagree_text = get_booking_text("consent_disagree_message")
    await callback.message.answer(disagree_text)
    await callback.answer()



