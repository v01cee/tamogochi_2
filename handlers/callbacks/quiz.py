import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery

from core.charts import generate_radar_chart
from core.keyboards import KeyboardOperations
from core.states import ProfileStates, QuizStates
from core.texts import get_booking_text
from database.session import get_session
from repositories.quiz_result_repository import QuizResultRepository
from repositories.user_repository import UserRepository

router = Router()
keyboard_ops = KeyboardOperations()
logger = logging.getLogger(__name__)


def _create_rating_keyboard():
    """Создает клавиатуру с кнопками 1-10 для оценки."""
    return {
        "1": "quiz_answer_1",
        "2": "quiz_answer_2",
        "3": "quiz_answer_3",
        "4": "quiz_answer_4",
        "5": "quiz_answer_5",
        "6": "quiz_answer_6",
        "7": "quiz_answer_7",
        "8": "quiz_answer_8",
        "9": "quiz_answer_9",
        "10": "quiz_answer_10",
    }


@router.callback_query(F.data == "more_details")
async def callback_more_details(callback: CallbackQuery, state: FSMContext):
    """Запуск квиза после экрана 'Подробнее'."""
    await callback.answer()
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение: {e}")
    
    text = get_booking_text("quiz_start")
    await callback.message.answer(text)

    question_1 = get_booking_text("quiz_question_1")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_1, reply_markup=rating_keyboard)

    await state.set_state(QuizStates.answering_question_1)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_1)
async def callback_quiz_answer_1(callback: CallbackQuery, state: FSMContext):
    """Ответ на первый вопрос (уровень энергии)."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_1=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    question_2 = get_booking_text("quiz_question_2")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_2, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_2)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_2)
async def callback_quiz_answer_2(callback: CallbackQuery, state: FSMContext):
    """Ответ на второй вопрос (уровень счастья)."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_2=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    question_3 = get_booking_text("quiz_question_3")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_3, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_3)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_3)
async def callback_quiz_answer_3(callback: CallbackQuery, state: FSMContext):
    """Ответ на третий вопрос (качество сна)."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_3=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    question_4 = get_booking_text("quiz_question_4")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_4, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_4)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_4)
async def callback_quiz_answer_4(callback: CallbackQuery, state: FSMContext):
    """Ответ на четвертый вопрос (качество значимых отношений)."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_4=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    question_5 = get_booking_text("quiz_question_5")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_5, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_5)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_5)
async def callback_quiz_answer_5(callback: CallbackQuery, state: FSMContext):
    """Ответ на пятый вопрос (баланс жизни)."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_5=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    question_6 = get_booking_text("quiz_question_6")
    rating_keyboard = await keyboard_ops.create_keyboard(
        buttons=_create_rating_keyboard(),
        interval=5,
    )
    await callback.message.answer(question_6, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_6)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_6)
async def callback_quiz_answer_6(callback: CallbackQuery, state: FSMContext):
    """Ответ на шестой вопрос (личная стратегия) и отправка диаграммы."""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_6=answer)
    await callback.answer(f"Вы выбрали: {answer}")

    data = await state.get_data()

    labels = ["Энергия", "Счастье", "Сон", "Отношения", "Баланс", "Стратегия"]

    def _safe_int(value):
        try:
            return int(value) if value is not None else 0
        except (TypeError, ValueError):
            return 0

    values = [
        _safe_int(data.get("question_1")),
        _safe_int(data.get("question_2")),
        _safe_int(data.get("question_3")),
        _safe_int(data.get("question_4")),
        _safe_int(data.get("question_5")),
        _safe_int(data.get("question_6")),
    ]

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

        quiz_repo = QuizResultRepository(session)
        quiz_repo.create_from_answers(user_id=user.id, answers=values)
    finally:
        session.close()

    result_text = get_booking_text("quiz_result")

    try:
        chart_bytes = generate_radar_chart(labels, values, title="Стартовый портрет")
    except ValueError:
        chart_bytes = None

    if chart_bytes:
        photo = BufferedInputFile(chart_bytes, filename="start_portrait.png")
        await callback.message.answer_photo(photo=photo, caption=result_text)
    else:
        await callback.message.answer(result_text)

    challenges_text = get_booking_text("challenges_request")
    await callback.message.answer(challenges_text)
    await state.set_state(ProfileStates.waiting_for_challenges)


