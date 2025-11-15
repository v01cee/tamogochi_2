import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards import KeyboardOperations
from core.states import FeedbackStates
from core.texts import get_booking_text

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


@router.callback_query(F.data == "feedback")
async def callback_feedback(callback: CallbackQuery, state: FSMContext):
    """Экран обратной связи."""
    text = get_booking_text("feedback_request")
    feedback_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Написать нам": "write_to_us_from_feedback",
            "<- Назад": "back_to_menu",
        },
        interval=2,
    )
    await callback.message.answer(text, reply_markup=feedback_keyboard)
    await callback.answer()


@router.callback_query(F.data == "write_to_us")
async def callback_write_to_us(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Написать нам' из главного меню."""
    text = get_booking_text("write_to_us_request")
    back_keyboard = await keyboard_ops.create_keyboard(
        buttons={"<- Назад": "back_to_menu"},
        interval=1,
    )
    await callback.message.answer(text, reply_markup=back_keyboard)
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback.answer()


@router.callback_query(F.data == "write_to_us_from_feedback")
async def callback_write_to_us_from_feedback(callback: CallbackQuery, state: FSMContext):
    """Запрос сообщения после выбора 'Написать нам' на экране обратной связи."""
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback.answer("Ожидаю ваше сообщение...")


