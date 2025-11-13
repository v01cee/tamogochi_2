import logging
import re
from datetime import time
from io import BytesIO
import requests

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.texts import get_booking_text
from core.keyboards import KeyboardOperations
from core.states import FeedbackStates, ProfileStates, NotificationSettingsStates, TouchQuestionStates
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
    # Пытаемся сохранить пользователя в БД, но не блокируем работу бота при ошибках
    try:
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
    except Exception as e:
        # Логируем ошибку, но продолжаем работу бота
        logger.warning(f"Не удалось сохранить пользователя в БД: {e}. Бот продолжает работу.")

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
        # Скачиваем голосовое сообщение и расшифровываем его
        processing_msg = None
        try:
            logger.info("Получено голосовое сообщение, начинаем транскрипцию...")
            
            # Отправляем промежуточное сообщение, чтобы Telegram не отключался по таймауту
            processing_msg = await message.answer("🔄 Обрабатываю голосовое сообщение...")
            logger.info("Отправлено промежуточное сообщение для предотвращения таймаута")
            
            # Получаем файл голосового сообщения
            file = await message.bot.get_file(message.voice.file_id)
            # Скачиваем файл
            audio_data = BytesIO()
            await message.bot.download_file(file.file_path, destination=audio_data)
            # Транскрибируем через Whisper
            transcribed_text = await transcribe_audio(audio_data)
            logger.info("Голосовое сообщение успешно расшифровано")
            
            # Удаляем промежуточное сообщение
            if processing_msg:
                try:
                    await processing_msg.delete()
                except Exception as e:
                    logger.warning(f"Не удалось удалить промежуточное сообщение: {e}")
            
            return transcribed_text.strip(), True
        except TimeoutError:
            logger.error("Таймаут при транскрипции голосового сообщения", exc_info=True)
            # Удаляем промежуточное сообщение при ошибке
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Ошибка при транскрипции голосового сообщения: {e}", exc_info=True)
            # Удаляем промежуточное сообщение при ошибке
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
            raise ValueError("Не удалось расшифровать голосовое сообщение. Попробуйте отправить текстовое сообщение.")

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
        f"Отформатируй список ответов участника курса. "
        f"ВАЖНО: Верни ТОЛЬКО форматированный список для раздела '{title}'. "
        f"НЕ добавляй информацию о других разделах (цели, вызовы и т.д.). "
        f"НЕ добавляй лишних комментариев или объяснений. "
        f"Верни только заголовок '{title}' и пункты списка под ним. "
        f"Формат: '{title}'\n\n- пункт 1\n- пункт 2\n- пункт 3\n\n"
        f"Ответы пользователя:\n{cleaned}"
    )

    try:
        result = (await generate_qwen_response(prompt)).strip()
        if result:
            # Убираем возможные дубликаты заголовка и лишние части
            # Оставляем только первую часть до следующего заголовка (если есть)
            lines = result.split('\n')
            filtered_lines = []
            found_title = False
            skip_until_title = False
            
            for line in lines:
                line_stripped = line.strip()
                # Если нашли наш заголовок, начинаем собирать
                if title.lower() in line_stripped.lower() and not found_title:
                    found_title = True
                    filtered_lines.append(line)
                    continue
                # Если нашли другой заголовок (цели/вызовы), останавливаемся
                if found_title and ('цели' in line_stripped.lower() or 'вызовы' in line_stripped.lower()) and title.lower() not in line_stripped.lower():
                    break
                # Если уже нашли заголовок, добавляем строки
                if found_title:
                    filtered_lines.append(line)
            
            # Если нашли заголовок, возвращаем отфильтрованный результат
            if found_title:
                result = '\n'.join(filtered_lines).strip()
            
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
    except ValueError as e:
        # Это наше сообщение о том, что нужно отправить текст
        error_msg = str(e)
        logger.info("Пользователь отправил голосовое сообщение, просим текст: %s", error_msg)
        await message.answer(error_msg)
        return
    except TimeoutError as e:
        logger.error("Таймаут при транскрипции: %s", e, exc_info=True)
        await message.answer("Сервер обрабатывает голосовое сообщение слишком долго. Попробуйте отправить более короткое сообщение или повторите попытку позже.")
        return
    except Exception as e:
        logger.error("Ошибка при извлечении текста: %s", e, exc_info=True)
        await message.answer("Пожалуйста, отправьте текстовое сообщение. Мы обработаем его с помощью ИИ для лучшего форматирования.")
        return

    if not challenges_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    # Сохраняем вызовы в state
    await state.update_data(challenges=challenges_text)
    
    # Получаем все данные для проверки
    data = await state.get_data()
    challenges = await _format_with_llm(data.get("challenges", "%N%"), "Ваши вызовы")
    goals = await _format_with_llm(data.get("goals", "%N%"), "Ваши цели")
    
    # Если цели уже есть, показываем данные для проверки (и вызовы, и цели)
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
        # Если целей еще нет, показываем только вызовы для проверки
        review_text = f"Ваши вызовы: {challenges}\n\nВсе верно?"
        review_buttons = {
            "Изменить": "edit_profile_data",
            "Все верно": "confirm_profile_data"
        }
        review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
        await message.answer(review_text, reply_markup=review_keyboard)


@router.message(ProfileStates.waiting_for_goals)
async def process_goals(message: Message, state: FSMContext):
    """Обработчик текстовых/голосовых сообщений для целей"""
    try:
        goals_text, is_voice = await _extract_text(message)
    except ValueError as e:
        # Это наше сообщение о том, что нужно отправить текст
        error_msg = str(e)
        logger.info("Пользователь отправил голосовое сообщение, просим текст: %s", error_msg)
        await message.answer(error_msg)
        return
    except TimeoutError as e:
        logger.error("Таймаут при транскрипции: %s", e, exc_info=True)
        await message.answer("Сервер обрабатывает голосовое сообщение слишком долго. Попробуйте отправить более короткое сообщение или повторите попытку позже.")
        return
    except Exception as e:
        logger.error("Ошибка при извлечении текста: %s", e, exc_info=True)
        await message.answer("Пожалуйста, отправьте текстовое сообщение. Мы обработаем его с помощью ИИ для лучшего форматирования.")
        return

    if not goals_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

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


@router.message(F.voice | F.text)
async def process_touch_question_answer(message: Message, state: FSMContext):
    """Обработчик ответов на вопросы касания (проверяет Redis для определения состояния)"""
    logger.info(f"[TOUCH_QUESTION] Проверяем Redis для определения состояния")
    
    # Сначала проверяем, есть ли состояние в Redis
    try:
        import redis
        from core.config import settings
        
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        
        bot_id = message.bot.id
        telegram_id = message.from_user.id
        state_key = f"fsm:{bot_id}:{telegram_id}:state"
        redis_state = redis_client.get(state_key)
        
        logger.info(f"[TOUCH_QUESTION] Состояние в Redis: {redis_state}, ключ: {state_key}")
        
        # Если состояние не TouchQuestionStates.waiting_for_answer, пропускаем
        if redis_state != "TouchQuestionStates:waiting_for_answer":
            logger.info(f"[TOUCH_QUESTION] Состояние не TouchQuestionStates.waiting_for_answer, пропускаем")
            return
        
        logger.info(f"[TOUCH_QUESTION] Состояние найдено в Redis, устанавливаем в FSM и обрабатываем")
        
        # Устанавливаем состояние в FSM
        await state.set_state(TouchQuestionStates.waiting_for_answer)
    except Exception as e:
        logger.error(f"[TOUCH_QUESTION] Ошибка при проверке Redis: {e}", exc_info=True)
        return
    
    # Продолжаем обработку
    await _process_touch_question_answer_internal(message, state)


@router.message(TouchQuestionStates.waiting_for_answer)
async def _process_touch_question_answer_internal(message: Message, state: FSMContext):
    """Внутренний обработчик ответов на вопросы касания"""
    logger.info(f"[TOUCH_QUESTION] Обработчик ответа на вопрос касания вызван")
    logger.info(f"[TOUCH_QUESTION] Тип сообщения: voice={message.voice is not None}, text={message.text is not None}")
    
    # Загружаем данные из Redis, если их нет в state
    try:
        import redis
        import json
        from core.config import settings
        
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        
        bot_id = message.bot.id
        telegram_id = message.from_user.id
        data_key = f"fsm:{bot_id}:{telegram_id}:data"
        
        # Загружаем данные из Redis
        redis_data = redis_client.get(data_key)
        if redis_data:
            logger.info(f"[TOUCH_QUESTION] Загружаем данные из Redis")
            data = json.loads(redis_data)
            questions_list_from_redis = data.get("questions_list", [])
            current_question_index_from_redis = data.get("current_question_index", 0)
            
            logger.info(f"[TOUCH_QUESTION] Данные из Redis: questions_list={len(questions_list_from_redis)}, current_question_index={current_question_index_from_redis}")
            logger.info(f"[TOUCH_QUESTION] Список вопросов из Redis: {questions_list_from_redis}")
            
            # Сохраняем в state для использования
            await state.update_data(
                touch_content_id=data.get("touch_content_id"),
                questions_list=questions_list_from_redis,
                current_question_index=current_question_index_from_redis,
                answers=data.get("answers", [])
            )
            logger.info(f"[TOUCH_QUESTION] Данные сохранены в state: questions_list={len(questions_list_from_redis)}, current_question_index={current_question_index_from_redis}")
        else:
            logger.warning(f"[TOUCH_QUESTION] Данные не найдены в Redis по ключу {data_key}")
            # Пробуем найти все ключи с этим пользователем
            pattern = f"fsm:*:{telegram_id}:data"
            all_keys = redis_client.keys(pattern)
            logger.info(f"[TOUCH_QUESTION] Найдены ключи Redis для пользователя {telegram_id}: {all_keys}")
            await message.answer("Ошибка: не найдены данные о вопросах. Попробуйте начать заново.")
            return
    except Exception as e:
        logger.error(f"[TOUCH_QUESTION] Ошибка при загрузке данных из Redis: {e}", exc_info=True)
        await message.answer("Ошибка при загрузке данных. Попробуйте начать заново.")
        return
    
    # Проверяем, голосовое ли сообщение
    if message.voice:
        logger.info(f"[TOUCH_QUESTION] Получено голосовое сообщение, показываем клавиатуру")
        # Сохраняем file_id голосового сообщения
        await state.update_data(voice_file_id=message.voice.file_id)
        
        # Показываем клавиатуру с кнопками "Перезаписать" и "Фиксируем"
        keyboard_buttons = {
            "Перезаписать": "touch_voice_rerecord",
            "Фиксируем": "touch_voice_confirm"
        }
        keyboard = await keyboard_ops.create_keyboard(buttons=keyboard_buttons, interval=2)
        
        await message.answer(
            "Отлично, хочешь ли ты еще раз перезаписать сообщение или фиксируем его для создания твоей личной карты стратегии?",
            reply_markup=keyboard
        )
        await state.set_state(TouchQuestionStates.waiting_for_voice_confirmation)
        return
    
    # Если текстовое сообщение - обрабатываем сразу
    answer_text = message.text
    if not answer_text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Обрабатываем текстовый ответ
    await _process_answer_with_validation(message, state, answer_text)


async def _process_answer_with_validation(message: Message, state: FSMContext, answer_text: str):
    """Обрабатывает ответ пользователя с валидацией через Qwen"""
    logger.info(f"[TOUCH_QUESTION] Начало обработки ответа с валидацией")
    
    # Получаем данные из state (или из Redis, если state пустой)
    data = await state.get_data()
    questions_list = data.get("questions_list", [])
    current_question_index = data.get("current_question_index", 0)
    answers = data.get("answers", [])
    
    logger.info(f"[TOUCH_QUESTION] Данные из state: questions_list={len(questions_list) if questions_list else 0}, current_question_index={current_question_index}")
    
    # Если данных нет в state, пробуем получить из Redis
    if not questions_list:
        try:
            import redis
            import json
            from core.config import settings
            
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
            
            bot_id = message.bot.id
            telegram_id = message.from_user.id
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            
            logger.info(f"[TOUCH_QUESTION] Пытаемся загрузить данные из Redis: key={data_key}")
            
            redis_data = redis_client.get(data_key)
            if redis_data:
                logger.info(f"[TOUCH_QUESTION] Данные найдены в Redis: {redis_data[:100]}...")
                data = json.loads(redis_data)
                questions_list = data.get("questions_list", [])
                current_question_index = data.get("current_question_index", 0)
                answers = data.get("answers", [])
                logger.info(f"[TOUCH_QUESTION] Загружено из Redis: questions_list={len(questions_list) if questions_list else 0}, current_question_index={current_question_index}")
                
                # Сохраняем в state для дальнейшего использования
                await state.update_data(
                    questions_list=questions_list,
                    current_question_index=current_question_index,
                    answers=answers,
                    touch_content_id=data.get("touch_content_id")
                )
            else:
                logger.warning(f"[TOUCH_QUESTION] Данные не найдены в Redis по ключу {data_key}")
                # Пробуем найти все ключи с этим пользователем
                pattern = f"fsm:*:{telegram_id}:data"
                all_keys = redis_client.keys(pattern)
                logger.info(f"[TOUCH_QUESTION] Найдены ключи Redis для пользователя {telegram_id}: {all_keys}")
        except Exception as e:
            logger.error(f"[TOUCH_QUESTION] Ошибка при загрузке данных из Redis: {e}", exc_info=True)
    
    if not questions_list:
        await message.answer("Ошибка: не найдены данные о вопросах. Попробуйте начать заново.")
        await state.clear()
        return
    
    # Получаем текущий вопрос для валидации
    if current_question_index >= len(questions_list):
        logger.error(f"[TOUCH_QUESTION] Индекс вопроса ({current_question_index}) больше количества вопросов ({len(questions_list)})")
        await message.answer("Ошибка: индекс вопроса некорректен. Попробуйте начать заново.")
        await state.clear()
        return
    
    if current_question_index < 0:
        logger.error(f"[TOUCH_QUESTION] Индекс вопроса ({current_question_index}) отрицательный")
        await message.answer("Ошибка: индекс вопроса некорректен. Попробуйте начать заново.")
        await state.clear()
        return
    
    current_question = questions_list[current_question_index]
    question_number = current_question_index + 1  # Номер вопроса для пользователя (начинается с 1)
    logger.info(f"[TOUCH_QUESTION] Валидируем ответ на вопрос #{question_number} (индекс {current_question_index}): {current_question[:100]}...")
    logger.info(f"[TOUCH_QUESTION] Всего вопросов: {len(questions_list)}, список: {[q[:50] for q in questions_list]}")
    
    # Отправляем промежуточное сообщение, чтобы Telegram не отключался по таймауту
    validation_msg = await message.answer("🔄 Анализирую ваш ответ...")
    
    # Отправляем ответ в Qwen для проверки
    try:
        validation_prompt = (
            f"Вопрос #{question_number}: {current_question}\n\n"
            f"Ответ пользователя: {answer_text}\n\n"
            "Проанализируй ответ пользователя на этот конкретный вопрос. "
            "Напиши короткое резюме (2-3 предложения) о правильности ответа, обращаясь к пользователю напрямую от первого лица (как в диалоге). "
            "Используй формулировки типа 'Ты...', 'В твоём ответе...', 'Тебе стоит...', 'Ты хорошо...' и т.д. "
            "НЕ просто говори 'правильно' или 'неправильно', а объясни ЧТО именно не так или что можно улучшить. "
            "Если ответ хороший, укажи что именно хорошо. "
            "Если есть проблемы, конкретно укажи что не так и что нужно исправить. "
            f"ВАЖНО: Пользователь отвечал именно на вопрос #{question_number}, не путай с другими вопросами."
        )
        
        logger.info(f"[TOUCH_QUESTION] Промпт для Qwen: Вопрос #{question_number}: {current_question[:50]}...")
        
        logger.info(f"[TOUCH_QUESTION] Отправляем ответ в Qwen для валидации")
        validation_result = await generate_qwen_response(validation_prompt)
        logger.info(f"[TOUCH_QUESTION] Получено резюме от Qwen: {validation_result}")
        
        # Удаляем промежуточное сообщение
        try:
            await validation_msg.delete()
        except:
            pass
        
        # Показываем резюме пользователю
        await message.answer(f"📝 Резюме по вашему ответу:\n\n{validation_result}")
    except Exception as e:
        logger.error(f"[TOUCH_QUESTION] Ошибка при валидации ответа через Qwen: {e}", exc_info=True)
        # Удаляем промежуточное сообщение
        try:
            await validation_msg.delete()
        except:
            pass
        # Продолжаем без валидации, если Qwen не ответил
        await message.answer("⚠️ Не удалось проанализировать ответ, но он сохранён. Продолжаем...")
    
    # Сохраняем ответ
    answers.append(answer_text)
    
    # Обновляем данные в state и Redis
    await state.update_data(
        questions_list=questions_list,
        current_question_index=current_question_index,
        answers=answers
    )
    
    # Также обновляем в Redis
    try:
        import redis
        import json
        from core.config import settings
        
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        
        bot_id = message.bot.id
        telegram_id = message.from_user.id
        data_key = f"fsm:{bot_id}:{telegram_id}:data"
        
        redis_client.set(
            data_key,
            json.dumps({
                "touch_content_id": data.get("touch_content_id"),
                "questions_list": questions_list,
                "current_question_index": current_question_index,
                "answers": answers
            }),
            ex=3600
        )
    except Exception as e:
        logger.warning(f"Не удалось обновить данные в Redis: {e}")
    
    # Проверяем, есть ли еще вопросы
    next_question_index = current_question_index + 1
    logger.info(f"[TOUCH_QUESTION] Текущий индекс: {current_question_index}, следующий: {next_question_index}, всего вопросов: {len(questions_list)}")
    
    if next_question_index < len(questions_list):
        # Отправляем следующий вопрос
        next_question = questions_list[next_question_index]
        logger.info(f"[TOUCH_QUESTION] Отправляем вопрос #{next_question_index + 1}: {next_question[:50]}...")
        await message.answer(next_question)
        
        # Обновляем состояние и данные
        await state.set_state(TouchQuestionStates.waiting_for_answer)
        await state.update_data(
            current_question_index=next_question_index,
            questions_list=questions_list,
            answers=answers,
            touch_content_id=data.get("touch_content_id")
        )
        
        # Обновляем индекс в Redis
        try:
            import redis
            import json
            from core.config import settings
            
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
            
            bot_id = message.bot.id
            telegram_id = message.from_user.id
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            
            # Обновляем данные в Redis с новым индексом
            redis_data_to_save = {
                "touch_content_id": data.get("touch_content_id"),
                "questions_list": questions_list,
                "current_question_index": next_question_index,
                "answers": answers
            }
            redis_client.set(data_key, json.dumps(redis_data_to_save), ex=3600)
            logger.info(f"[TOUCH_QUESTION] Обновлен индекс в Redis: {next_question_index} (вопрос #{next_question_index + 1})")
            
            # Проверяем, что данные сохранились правильно
            saved_data = json.loads(redis_client.get(data_key))
            logger.info(f"[TOUCH_QUESTION] Проверка: сохраненный индекс в Redis = {saved_data.get('current_question_index')}")
        except Exception as e:
            logger.error(f"[TOUCH_QUESTION] Ошибка при обновлении индекса в Redis: {e}", exc_info=True)
    else:
        # Все вопросы отвечены
        await message.answer("Спасибо за ответы! Мы собрали их в вашу личную карту стратегий.")
        await state.clear()
        
        # Очищаем данные из Redis
        try:
            bot_id = message.bot.id
            telegram_id = message.from_user.id
            state_key = f"fsm:{bot_id}:{telegram_id}:state"
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            redis_client.delete(state_key, data_key)
        except:
            pass


@router.message(F.voice)
async def handle_voice_message(message: Message, state: FSMContext):
    """Универсальный обработчик голосовых сообщений:
    1. Скачивает голосовое сообщение
    2. Расшифровывает через Whisper
    3. Отправляет в Qwen для форматирования (убрать лишнее, выписать ключевые вызовы)
    4. Возвращает результат пользователю
    """
    # Проверяем, есть ли активное состояние FSM (включая Redis)
    current_state = await state.get_state()
    
    # Также проверяем Redis на случай, если состояние установлено из админки
    try:
        import redis
        import json
        from core.config import settings
        
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        
        bot_id = message.bot.id
        telegram_id = message.from_user.id
        state_key = f"fsm:{bot_id}:{telegram_id}:state"
        redis_state = redis_client.get(state_key)
        
        if redis_state == "TouchQuestionStates:waiting_for_answer":
            # Пользователь ожидает ответ на вопрос касания, устанавливаем состояние
            await state.set_state(TouchQuestionStates.waiting_for_answer)
            current_state = TouchQuestionStates.waiting_for_answer
    except Exception as e:
        logger.warning(f"Не удалось проверить состояние в Redis: {e}")
    
    logger.info(f"[VOICE] Проверка FSM состояния: {current_state}")
    
    # Если пользователь в состоянии ожидания ответа на вопрос касания - пропускаем
    # Пусть обрабатывает специфичный обработчик process_touch_question_answer
    if current_state == TouchQuestionStates.waiting_for_answer:
        logger.info(f"[VOICE] Пользователь в состоянии TouchQuestionStates.waiting_for_answer, пропускаем универсальный обработчик")
        return
    
    if current_state is not None:
        # Если пользователь в другом состоянии FSM, пропускаем обработку
        # Пусть обрабатывают специфичные обработчики состояний через _extract_text
        logger.info(f"[VOICE] Пользователь в FSM состоянии {current_state}, пропускаем универсальный обработчик")
        return
    
    # Обрабатываем голосовое сообщение только если пользователь НЕ в состоянии FSM
    processing_msg = None
    try:
        user_id = message.from_user.id
        logger.info(f"[VOICE] ===== НАЧАЛО ОБРАБОТКИ ГОЛОСОВОГО СООБЩЕНИЯ =====")
        logger.info(f"[VOICE] Пользователь ID: {user_id}")
        logger.info(f"[VOICE] File ID: {message.voice.file_id}")
        logger.info(f"[VOICE] Длительность: {message.voice.duration} сек")
        logger.info(f"[VOICE] Размер файла: {message.voice.file_size} байт")
        
        # Отправляем промежуточное сообщение, чтобы Telegram не отключался по таймауту
        processing_msg = await message.answer("🔄 Обрабатываю голосовое сообщение...")
        logger.info(f"[VOICE] Отправлено промежуточное сообщение для предотвращения таймаута")
        
        # Шаг 1: Скачиваем голосовое сообщение
        logger.info(f"[VOICE] ШАГ 1: Получаем информацию о файле...")
        file = await message.bot.get_file(message.voice.file_id)
        logger.info(f"[VOICE] Путь к файлу: {file.file_path}")
        logger.info(f"[VOICE] Размер файла: {file.file_size} байт")
        
        logger.info(f"[VOICE] ШАГ 1: Скачиваем файл...")
        audio_data = BytesIO()
        await message.bot.download_file(file.file_path, destination=audio_data)
        audio_size = len(audio_data.getvalue())
        logger.info(f"[VOICE] ✓ Файл успешно скачан! Размер: {audio_size} байт")
        
        # Шаг 2: Преобразуем аудио в текст через Whisper
        logger.info(f"[VOICE] ШАГ 2: Отправляем аудио файл в Whisper для преобразования в текст...")
        logger.info(f"[VOICE] Размер данных для отправки: {audio_size} байт")
        
        transcribed_text = await transcribe_audio(audio_data)
        
        if not transcribed_text or not transcribed_text.strip():
            logger.warning(f"[VOICE] ✗ Whisper вернул пустой текст!")
            await message.answer("Не удалось распознать речь в голосовом сообщении. Попробуйте записать заново.")
            return
        
        logger.info(f"[VOICE] ✓ Whisper успешно преобразовал аудио в текст!")
        logger.info(f"[VOICE] Длина расшифрованного текста: {len(transcribed_text)} символов")
        logger.info(f"[VOICE] Полный текст расшифровки: {transcribed_text}")
        
        # Шаг 3: Отправляем в Qwen для форматирования
        logger.info(f"[VOICE] ШАГ 3: Отправляем расшифрованный текст в Qwen для обработки...")
        qwen_prompt = (
            "Извлеки из текста ТОЛЬКО те вызовы/проблемы, которые упомянул пользователь.\n\n"
            f"Исходный текст пользователя: {transcribed_text.strip()}\n\n"
            "КРИТИЧЕСКИ ВАЖНО:\n"
            "- Верни ТОЛЬКО то, что есть в тексте выше. НЕ додумывай, НЕ интерпретируй, НЕ добавляй от себя.\n"
            "- Если в тексте нет явных вызовов, верни пустую строку.\n"
            "- Формат ответа (БЕЗ заголовков, БЕЗ дополнительных слов):\n"
            "- вызов 1\n"
            "- вызов 2\n"
            "- вызов 3\n\n"
            "ЗАПРЕЩЕНО:\n"
            "- Добавлять заголовки типа 'Ваши вызовы', 'Цели' и т.д.\n"
            "- Добавлять информацию о целях или других разделах\n"
            "- Додумывать вызовы, которых нет в исходном тексте\n"
            "- Добавлять комментарии или объяснения\n\n"
            "Верни ТОЛЬКО список вызовов из текста, без заголовков и лишних слов."
        )
        logger.info(f"[VOICE] Промпт для Qwen: {qwen_prompt[:200]}...")
        
        formatted_text = None
        try:
            formatted_text = await generate_qwen_response(qwen_prompt)
            logger.info(f"[VOICE] ✓ Qwen успешно обработал текст!")
            logger.info(f"[VOICE] Длина обработанного текста: {len(formatted_text)} символов")
            logger.info(f"[VOICE] Результат от Qwen: {formatted_text}")
        except (TimeoutError, requests.exceptions.Timeout, requests.exceptions.ReadTimeout) as e:
            logger.warning(f"[VOICE] Таймаут при запросе к Qwen: {e}")
            logger.info(f"[VOICE] Qwen не ответил, попросим пользователя написать вручную")
            formatted_text = None
        except Exception as e:
            logger.error(f"[VOICE] Ошибка при запросе к Qwen: {e}", exc_info=True)
            logger.info(f"[VOICE] Qwen не ответил, попросим пользователя написать вручную")
            formatted_text = None
        
        # Очищаем результат от лишних заголовков, разделов и додумок
        # Если Qwen не ответил (таймаут или ошибка), попросим написать вручную
        if formatted_text is None:
            logger.info(f"[VOICE] Qwen не ответил, отправляем просьбу написать вручную")
            # Удаляем промежуточное сообщение
            if processing_msg:
                try:
                    await processing_msg.delete()
                    logger.info(f"[VOICE] Промежуточное сообщение удалено")
                except Exception as e:
                    logger.warning(f"[VOICE] Не удалось удалить промежуточное сообщение: {e}")
            
            # Просим написать вручную
            await message.answer(
                "✍️ Теперь Расскажите 1–3 ключевых вызова, которые стоят перед вами прямо сейчас.\n"
                "Например: «не хватает энергии», «хочу больше времени для семьи», «нужна ясность в делах».\n"
                "(Эти ответы тоже войдут в ваш артефакт.)"
            )
            logger.info(f"[VOICE] ✓ Отправлена просьба написать вручную")
            logger.info(f"[VOICE] ===== ОБРАБОТКА ЗАВЕРШЕНА =====")
            return
        else:
            cleaned_text = formatted_text.strip()
            lines = cleaned_text.split('\n')
            filtered_lines = []
            found_list_start = False
            
            # Список ключевых слов, которые указывают на начало нежелательных разделов
            unwanted_keywords = [
                'ваши цели', 'цели:', 'цели\n', 'цели ', 
                'ваши вызовы:', 'вызовы:', 'вызовы\n', 'вызовы ',
                'например', 'пример:', 'примеры'
            ]
            
            for line in lines:
                line_stripped = line.strip()
                line_lower = line_stripped.lower()
                
                # Пропускаем пустые строки в начале
                if not found_list_start and not line_stripped:
                    continue
                
                # Если встретили раздел целей - останавливаемся
                if 'цели' in line_lower and 'вызовы' not in line_lower:
                    logger.info(f"[VOICE] Обнаружен раздел целей, останавливаем фильтрацию: {line_stripped}")
                    break
                
                # Пропускаем заголовки и нежелательные разделы
                if any(keyword in line_lower for keyword in unwanted_keywords):
                    # Если это заголовок "Ваши вызовы" или просто "Вызовы" - пропускаем, но продолжаем
                    if ('вызовы' in line_lower and 'цели' not in line_lower) or line_lower == 'вызовы':
                        logger.info(f"[VOICE] Пропускаем заголовок: {line_stripped}")
                        continue
                    # Если это другие нежелательные слова - пропускаем
                    if any(unwanted in line_lower for unwanted in ['цели', 'например', 'пример']):
                        logger.info(f"[VOICE] Пропускаем нежелательную строку: {line_stripped}")
                        continue
                
                # Берем только строки, которые выглядят как пункты списка (начинаются с -, •, или цифры)
                if line_stripped.startswith(('-', '•', '*')) or (line_stripped and line_stripped[0].isdigit()):
                    found_list_start = True
                    filtered_lines.append(line_stripped)
                elif found_list_start and line_stripped:
                    # Если уже начали собирать список, но встретили не-пункт - возможно, это конец списка
                    # Проверяем, не является ли это началом нового раздела
                    if any(unwanted in line_lower for unwanted in ['цели', 'например', 'пример', 'ваши']):
                        break
                    # Если это продолжение предыдущего пункта (многострочный), добавляем
                    if filtered_lines:
                        filtered_lines.append(line_stripped)
            
            cleaned_text = '\n'.join(filtered_lines).strip()
            logger.info(f"[VOICE] Отфильтрованный текст (только вызовы): {cleaned_text}")
            
            # Если после фильтрации ничего не осталось, используем исходный текст (но без заголовков и целей)
            if not cleaned_text:
                logger.warning(f"[VOICE] После фильтрации результат пустой, пытаемся извлечь из исходного ответа Qwen")
                # Пытаемся извлечь хотя бы что-то из исходного ответа
                original_lines = formatted_text.strip().split('\n')
                temp_lines = []
                found_goals_section = False
                
                for line in original_lines:
                    line_stripped = line.strip()
                    line_lower = line_stripped.lower()
                    
                    # Если встретили раздел целей - останавливаемся
                    if 'цели' in line_lower and 'вызовы' not in line_lower:
                        found_goals_section = True
                        break
                    
                    # Пропускаем заголовки
                    if any(keyword in line_lower for keyword in ['ваши вызовы', 'вызовы:', 'ваши цели']):
                        continue
                    
                    # Берем все строки, которые не пустые и не являются заголовками
                    if line_stripped and not found_goals_section:
                        temp_lines.append(line_stripped)
                
                if temp_lines:
                    cleaned_text = '\n'.join(temp_lines).strip()
                    logger.info(f"[VOICE] Извлечен текст из исходного ответа: {cleaned_text}")
                
                # Если все еще пусто после всех попыток извлечения, отправляем просьбу написать вручную
                if not cleaned_text:
                    logger.warning(f"[VOICE] Не удалось извлечь вызовы из ответа Qwen, попросим написать вручную")
                    # Удаляем промежуточное сообщение
                    if processing_msg:
                        try:
                            await processing_msg.delete()
                            logger.info(f"[VOICE] Промежуточное сообщение удалено")
                        except Exception as e:
                            logger.warning(f"[VOICE] Не удалось удалить промежуточное сообщение: {e}")
                    
                    # Просим написать вручную
                    await message.answer(
                        "✍️ Теперь Расскажите 1–3 ключевых вызова, которые стоят перед вами прямо сейчас.\n"
                        "Например: «не хватает энергии», «хочу больше времени для семьи», «нужна ясность в делах».\n"
                        "(Эти ответы тоже войдут в ваш артефакт.)"
                    )
                    logger.info(f"[VOICE] ✓ Отправлена просьба написать вручную")
                    logger.info(f"[VOICE] ===== ОБРАБОТКА ЗАВЕРШЕНА =====")
                    return
        
        # Шаг 4: Возвращаем результат пользователю
        logger.info(f"[VOICE] ШАГ 4: Отправляем результат пользователю...")
        logger.info(f"[VOICE] Финальный cleaned_text: '{cleaned_text}' (длина: {len(cleaned_text) if cleaned_text else 0})")
        
        if cleaned_text:
            result_message = (
                "✍️ Теперь Расскажите 1–3 ключевых вызова, которые стоят перед вами прямо сейчас.\n"
                "Например: «не хватает энергии», «хочу больше времени для семьи», «нужна ясность в делах».\n"
                "(Эти ответы тоже войдут в ваш артефакт.)\n\n"
                f"{cleaned_text}"
            )
        else:
            # Если все равно пусто, отправляем только инструкцию
            logger.warning(f"[VOICE] Не удалось извлечь вызовы из ответа Qwen, отправляем только инструкцию")
            result_message = (
                "✍️ Теперь Расскажите 1–3 ключевых вызова, которые стоят перед вами прямо сейчас.\n"
                "Например: «не хватает энергии», «хочу больше времени для семьи», «нужна ясность в делах».\n"
                "(Эти ответы тоже войдут в ваш артефакт.)"
            )
        
        logger.info(f"[VOICE] Готовимся отправить сообщение длиной: {len(result_message)} символов")
        logger.info(f"[VOICE] Содержимое сообщения: {result_message[:200]}...")
        
        # Удаляем промежуточное сообщение и отправляем результат
        if processing_msg:
            try:
                await processing_msg.delete()
                logger.info(f"[VOICE] Промежуточное сообщение удалено")
            except Exception as e:
                logger.warning(f"[VOICE] Не удалось удалить промежуточное сообщение: {e}")
        
        try:
            await message.answer(result_message)
            logger.info(f"[VOICE] ✓ Результат успешно отправлен пользователю!")
            logger.info(f"[VOICE] ===== ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО =====")
        except Exception as e:
            logger.error(f"[VOICE] ОШИБКА при отправке сообщения: {e}", exc_info=True)
            raise
            
    except TimeoutError:
        logger.error("[VOICE] Таймаут при обработке голосового сообщения", exc_info=True)
        # Удаляем промежуточное сообщение, если оно было отправлено
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        await message.answer("Сервер обрабатывает голосовое сообщение слишком долго. Попробуйте отправить более короткое сообщение или повторите попытку позже.")
    except Exception as e:
        logger.error(f"[VOICE] Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        # Удаляем промежуточное сообщение, если оно было отправлено
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        await message.answer("Произошла ошибка при обработке голосового сообщения. Попробуйте отправить текстовое сообщение или повторите попытку позже.")

