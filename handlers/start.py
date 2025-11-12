import logging
import re
from datetime import time
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.texts import get_booking_text
from core.keyboards import KeyboardOperations
from core.states import FeedbackStates, ProfileStates, NotificationSettingsStates
from database.session import get_session
from repositories.user_repository import UserRepository
from qwen_client import generate_qwen_response
from whisper_client import transcribe_audio

router = Router()
keyboard_ops = KeyboardOperations()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    session_gen = get_session()
    session = next(session_gen)
    try:
        user_repo = UserRepository(session)
        user_repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code
        )
    finally:
        session.close()

    text = get_booking_text("start")
    await message.answer(text)
    
    # Отправляем второе сообщение курса
    step_1_text = get_booking_text("step_1")
    await message.answer(step_1_text)
    
    # Отправляем третье сообщение с кнопкой "Старт"
    step_2_text = get_booking_text("step_2")
    start_buttons = {
        "Старт": "course_start"
    }
    start_keyboard = await keyboard_ops.create_keyboard(buttons=start_buttons, interval=1)
    await message.answer(step_2_text, reply_markup=start_keyboard)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    text = get_booking_text("help")
    await message.answer(text)


@router.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для обратной связи"""
    # Здесь можно сохранить обратную связь в базу данных
    feedback_text = message.text
    
    # Отправляем сообщение
    feedback_request_text = get_booking_text("feedback_request")
    await message.answer(feedback_request_text)
    
    # Очищаем состояние
    await state.clear()
    
    # Возвращаем в главное меню
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await message.answer(step_6_text, reply_markup=menu_keyboard)


async def _extract_text(message: Message) -> tuple[str, bool]:
    """Получить текст ответа, при необходимости расшифровать голос."""
    if message.text:
        return message.text.strip(), False

    if message.caption:
        return message.caption.strip(), False

    if message.voice:
        audio_buffer = BytesIO()
        await message.bot.download(message.voice.file_id, destination=audio_buffer)
        transcription = (await transcribe_audio(audio_buffer)).strip()
        return transcription, True

    return "", False


def _parse_notification_time(text: str) -> time | None:
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


def _fallback_format(text: str) -> str:
    """Базовое форматирование списка пунктов."""
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned

    parts = [
        part.strip("•- \t")
        for part in re.split(r"[\n;]+", cleaned)
        if part and part.strip()
    ]
    if len(parts) <= 1:
        return cleaned
    return "\n".join(f"• {part}" for part in parts)


async def _format_with_llm(text: str, title: str) -> str:
    """Отдать текст в Qwen для аккуратного форматирования."""
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned

    prompt = (
        "Отформатируй список ответов участника курса. "
        "Выведи короткий заголовок и пункты списка, сохраняя смысл. "
        "Не добавляй лишних комментариев, верни только текст. "
        f"Заголовок: {title}. Ответы:\n{cleaned}"
    )

    try:
        result = (await generate_qwen_response(prompt)).strip()
        if result:
            return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Не удалось получить форматирование от Qwen: %s", exc)

    return _fallback_format(cleaned)


@router.message(ProfileStates.waiting_for_challenges)
async def process_challenges(message: Message, state: FSMContext):
    """Обработчик текстовых/голосовых сообщений для вызовов"""
    try:
        challenges_text, is_voice = await _extract_text(message)
    except Exception:
        await message.answer("Не удалось распознать голосовое сообщение. Отправьте текст или повторите попытку.")
        return

    if not challenges_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение или голосовое сообщение.")
        return

    if is_voice:
        await message.answer(f"Записала: {challenges_text}")

    # Сохраняем вызовы в state
    await state.update_data(challenges=challenges_text)
    
    # Получаем все данные для проверки
    data = await state.get_data()
    challenges = await _format_with_llm(data.get("challenges", "%N%"), "Ваши вызовы")
    goals = await _format_with_llm(data.get("goals", "%N%"), "Ваши цели")
    
    # Если цели уже есть, показываем данные для проверки
    if goals != "%N%":
        # Показываем данные для проверки
        review_text = get_booking_text("data_review").replace("%N%", challenges, 1).replace("%N%", goals, 1)
        review_buttons = {
            "Изменить": "edit_profile_data",
            "Все верно": "confirm_profile_data"
        }
        review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
        await message.answer(review_text, reply_markup=review_keyboard)
    else:
        # Переходим к запросу целей
        goals_text = get_booking_text("goals_request")
        await message.answer(goals_text)
        await state.set_state(ProfileStates.waiting_for_goals)


@router.message(ProfileStates.waiting_for_goals)
async def process_goals(message: Message, state: FSMContext):
    """Обработчик текстовых/голосовых сообщений для целей"""
    try:
        goals_text, is_voice = await _extract_text(message)
    except Exception:
        await message.answer("Не удалось распознать голосовое сообщение. Отправьте текст или повторите попытку.")
        return

    if not goals_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение или голосовое сообщение.")
        return

    if is_voice:
        await message.answer(f"Записала: {goals_text}")

    # Сохраняем цели в state
    await state.update_data(goals=goals_text)
    
    # Показываем сообщение "принято!"
    accepted_text = get_booking_text("data_accepted")
    await message.answer(accepted_text)
    
    # Получаем все данные для проверки
    data = await state.get_data()
    challenges = await _format_with_llm(data.get("challenges", "%N%"), "Ваши вызовы")
    goals = await _format_with_llm(data.get("goals", "%N%"), "Ваши цели")
    
    # Показываем данные для проверки
    review_text = get_booking_text("data_review").replace("%N%", challenges, 1).replace("%N%", goals, 1)
    review_buttons = {
        "Изменить": "edit_profile_data",
        "Все верно": "confirm_profile_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)


@router.message(NotificationSettingsStates.waiting_for_time)
async def process_notification_time_input(message: Message, state: FSMContext):
    """Обработка времени уведомлений, введённого пользователем."""
    entered_time = _parse_notification_time(message.text or "")
    if entered_time is None:
        await message.answer(get_booking_text("notification_time_error"))
        return

    data = await state.get_data()
    touch_type = data.get("selected_touch")
    touch_label = data.get("touch_label", "")

    if not touch_type:
        await state.clear()
        await message.answer("Что-то пошло не так, попробуй начать настройку заново.")
        return

    session = next(get_session())
    try:
        repo = UserRepository(session)
        user = repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )
        repo.set_notification_time(user, touch_type, entered_time)
    finally:
        session.close()

    confirmation = get_booking_text("notification_time_saved").format(
        touch_label=touch_label,
        time=entered_time.strftime("%H:%M"),
    )
    await message.answer(confirmation)

    buttons = {
        "Настроить ещё": "notification_customize",
        "В главное меню": "back_to_menu",
    }
    keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=1)
    await message.answer("Выбери следующий шаг:", reply_markup=keyboard)
    await state.set_state(NotificationSettingsStates.choosing_touch)


@router.message(ProfileStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для имени и фамилии"""
    name_text = message.text or (message.caption if message.caption else "")
    
    if not name_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Проверяем, что есть 2 слова через пробел
    name_parts = name_text.strip().split()
    if len(name_parts) < 2:
        await message.answer("Пожалуйста, укажите имя и фамилию через пробел.")
        return
    
    # Сохраняем имя в state
    full_name = " ".join(name_parts)
    await state.update_data(full_name=full_name)
    
    # Проверяем наличие username в Telegram
    username = message.from_user.username
    
    if username:
        # Показываем подтверждение ника
        username_confirm_text = get_booking_text("username_confirm").replace("%NNN%", f"@{username}")
        username_buttons = {
            "ДА": "username_confirm_yes",
            "НЕТ": "username_confirm_no"
        }
        username_keyboard = await keyboard_ops.create_keyboard(buttons=username_buttons, interval=2)
        await message.answer(username_confirm_text, reply_markup=username_keyboard)
        await state.update_data(username=username)
    else:
        # Запрашиваем ник
        username_text = get_booking_text("username_request")
        await message.answer(username_text)
        await state.set_state(ProfileStates.waiting_for_username)


@router.message(ProfileStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для ника в Telegram"""
    username_text = message.text or (message.caption if message.caption else "")
    
    if not username_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Убираем @ если есть
    username = username_text.strip().lstrip("@")
    
    # Сохраняем ник в state
    await state.update_data(username=username)
    
    # Показываем подтверждение ника
    username_confirm_text = get_booking_text("username_confirm").replace("%NNN%", f"@{username}")
    username_buttons = {
        "ДА": "username_confirm_yes",
        "НЕТ": "username_confirm_no"
    }
    username_keyboard = await keyboard_ops.create_keyboard(buttons=username_buttons, interval=2)
    await message.answer(username_confirm_text, reply_markup=username_keyboard)


@router.message(ProfileStates.editing_name)
async def process_editing_name(message: Message, state: FSMContext):
    """Обработчик редактирования имени"""
    name_text = message.text or (message.caption if message.caption else "")
    
    if not name_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Проверяем, что есть 2 слова через пробел
    name_parts = name_text.strip().split()
    if len(name_parts) < 2:
        await message.answer("Пожалуйста, укажите имя и фамилию через пробел.")
        return
    
    # Сохраняем имя в state
    full_name = " ".join(name_parts)
    await state.update_data(full_name=full_name)
    
    # Показываем данные для проверки
    data = await state.get_data()
    full_name = data.get("full_name", "%N%")
    role = data.get("role", "%N%")
    company = data.get("company", "%N%")
    
    review_text = get_booking_text("profile_data_review")
    review_text = review_text.replace("%N%", full_name, 1)
    review_text = review_text.replace("%N%", role, 1)
    review_text = review_text.replace("%N%", company, 1)
    
    review_buttons = {
        "Изменить": "edit_profile_personal_data",
        "Верно": "confirm_profile_personal_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)


@router.message(ProfileStates.editing_role)
async def process_editing_role(message: Message, state: FSMContext):
    """Обработчик редактирования роли"""
    role_text = message.text or (message.caption if message.caption else "")
    
    if not role_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Сохраняем роль в state
    await state.update_data(role=role_text.strip())
    
    # Показываем данные для проверки
    data = await state.get_data()
    full_name = data.get("full_name", "%N%")
    role = data.get("role", "%N%")
    company = data.get("company", "%N%")
    
    review_text = get_booking_text("profile_data_review")
    review_text = review_text.replace("%N%", full_name, 1)
    review_text = review_text.replace("%N%", role, 1)
    review_text = review_text.replace("%N%", company, 1)
    
    review_buttons = {
        "Изменить": "edit_profile_personal_data",
        "Верно": "confirm_profile_personal_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)


@router.message(ProfileStates.editing_company)
async def process_editing_company(message: Message, state: FSMContext):
    """Обработчик редактирования компании"""
    company_text = message.text or (message.caption if message.caption else "")
    
    if not company_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Сохраняем компанию в state
    await state.update_data(company=company_text.strip())
    
    # Показываем данные для проверки
    data = await state.get_data()
    full_name = data.get("full_name", "%N%")
    role = data.get("role", "%N%")
    company = data.get("company", "%N%")
    
    review_text = get_booking_text("profile_data_review")
    review_text = review_text.replace("%N%", full_name, 1)
    review_text = review_text.replace("%N%", role, 1)
    review_text = review_text.replace("%N%", company, 1)
    
    review_buttons = {
        "Изменить": "edit_profile_personal_data",
        "Верно": "confirm_profile_personal_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)


@router.message(ProfileStates.waiting_for_role)
async def process_role(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для роли (если выбрано 'другое')"""
    role_text = message.text or (message.caption if message.caption else "")
    
    if not role_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Сохраняем роль в state
    await state.update_data(role=role_text.strip())
    
    # Переходим к запросу компании
    company_text = get_booking_text("company_request")
    await message.answer(company_text)
    await state.set_state(ProfileStates.waiting_for_company)


@router.message(ProfileStates.waiting_for_company)
async def process_company(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для компании"""
    company_text = message.text or (message.caption if message.caption else "")
    
    if not company_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Сохраняем компанию в state
    await state.update_data(company=company_text.strip())
    
    # Показываем сообщение "принято!"
    accepted_text = get_booking_text("profile_data_accepted")
    await message.answer(accepted_text)
    
    # Получаем все данные для проверки
    data = await state.get_data()
    full_name = data.get("full_name", "%N%")
    role = data.get("role", "%N%")
    company = data.get("company", "%N%")
    
    # Показываем данные для проверки
    review_text = get_booking_text("profile_data_review")
    review_text = review_text.replace("%N%", full_name, 1)
    review_text = review_text.replace("%N%", role, 1)
    review_text = review_text.replace("%N%", company, 1)
    
    review_buttons = {
        "Изменить": "edit_profile_personal_data",
        "Верно": "confirm_profile_personal_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)

