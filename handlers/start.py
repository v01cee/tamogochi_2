import asyncio
import logging
import re
from datetime import date, time
from io import BytesIO
import requests

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.texts import get_booking_text
from core.keyboards import KeyboardOperations
from core.states import FeedbackStates, ProfileStates, NotificationSettingsStates, TouchQuestionStates, SaturdayReflectionStates
from database.session import get_session
from repositories.user_repository import UserRepository
from repositories.touch_answer_repository import TouchAnswerRepository
from repositories.touch_content_repository import TouchContentRepository
from repositories.evening_reflection_repository import EveningReflectionRepository
from qwen_client import generate_qwen_response
from whisper_client import transcribe_audio

router = Router()
keyboard_ops = KeyboardOperations()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    # Пытаемся сохранить пользователя в БД, но не блокируем работу бота при ошибках
    user = None
    try:
        session_gen = get_session()
        session = next(session_gen)
        try:
            user_repo = UserRepository(session)
            user = user_repo.get_or_create(
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

    # Если пользователь не первый раз в боте, сразу показываем главное меню
    if user and not user.is_first_visit:
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
        return

    # Если первый визит, показываем вводные сообщения
    try:
        text = get_booking_text("start")
        if text:
            await message.answer(text)
            logger.info(f"[START] Отправлено первое сообщение для пользователя {message.from_user.id}")
            # Небольшая задержка между сообщениями
            await asyncio.sleep(0.5)
        
        # Отправляем второе сообщение курса
        step_1_text = get_booking_text("step_1")
        if step_1_text:
            await message.answer(step_1_text)
            logger.info(f"[START] Отправлено второе сообщение для пользователя {message.from_user.id}")
            # Небольшая задержка между сообщениями
            await asyncio.sleep(0.5)
        else:
            logger.warning(f"[START] step_1_text пустой для пользователя {message.from_user.id}")
        
        # Отправляем третье сообщение с кнопкой "Старт"
        step_2_text = get_booking_text("step_2")
        if step_2_text:
            start_buttons = {
                "Старт": "course_start"
            }
            start_keyboard = await keyboard_ops.create_keyboard(buttons=start_buttons, interval=1)
            await message.answer(step_2_text, reply_markup=start_keyboard)
            logger.info(f"[START] Отправлено третье сообщение с кнопкой для пользователя {message.from_user.id}")
        else:
            logger.warning(f"[START] step_2_text пустой для пользователя {message.from_user.id}")
    except Exception as e:
        logger.error(f"[START] Ошибка при отправке вводных сообщений для пользователя {message.from_user.id}: {e}", exc_info=True)
        # Пытаемся отправить хотя бы основное сообщение
        try:
            await message.answer("Произошла ошибка при загрузке вводных сообщений. Пожалуйста, попробуйте позже или напишите нам.")
        except:
            pass


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
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем сообщение благодарности с клавиатурой главного меню
    feedback_thanks_text = get_booking_text("feedback_thanks")
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    
    # Отправляем благодарность
    await message.answer(feedback_thanks_text)
    
    # Отправляем главное меню с клавиатурой
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
    
    # Проверка на бессмысленный/слишком короткий текст
    if len(cleaned) < 3:
        logger.warning(f"Текст слишком короткий для обработки: '{cleaned}'")
        return f"[Не удалось разобрать текст: '{cleaned}'. Пожалуйста, напишите более подробно.]"
    
    # Проверка на случайные символы без пробелов (если текст короткий и без пробелов)
    if len(cleaned) < 20 and ' ' not in cleaned:
        # Проверяем, есть ли хотя бы одна русская или английская буква
        has_letters = any(c.isalpha() for c in cleaned)
        if not has_letters:
            logger.warning(f"Текст содержит только не-буквенные символы: '{cleaned}'")
            return f"[Не удалось разобрать текст: '{cleaned}'. Пожалуйста, напишите более подробно.]"
    
    prompt = (
        f"Отформатируй список ответов участника курса.\n"
        f"Раздел: '{title}'.\n"
        f"ВАЖНО:\n"
        f"- Если текст непонятный, бессмысленный, слишком короткий или похож на случайные символы - верни ТОЧНО эту строку: 'UNPARSEABLE_TEXT'\n"
        f"- Верни ТОЛЬКО пункты списка, без заголовка.\n"
        f"- НЕ добавляй слова 'Ваши цели', 'Ваши вызовы', 'Цели', 'Вызовы' и т.п. в начале.\n"
        f"- НЕ добавляй лишних комментариев или объяснений.\n"
        f"- НЕ выдумывай и не придумывай пункты, которых нет в тексте пользователя.\n"
        f"- Если в тексте пользователя нет осмысленных пунктов - верни 'UNPARSEABLE_TEXT'.\n"
        f"Формат: '- пункт 1\\n- пункт 2\\n- пункт 3'.\n\n"
        f"Ответы пользователя:\n{cleaned}"
    )

    try:
        result = (await generate_qwen_response(prompt)).strip()
        if result:
            # Проверяем, не вернула ли модель маркер о непонятном тексте
            if "UNPARSEABLE_TEXT" in result.upper():
                logger.warning(f"Qwen не смог разобрать текст: '{cleaned}'")
                return f"[Не удалось разобрать текст: '{cleaned}'. Пожалуйста, напишите более подробно.]"
            
            # 1) Срезаем всё после возможного второго заголовка (цели/вызовы) —
            # на случай если модель вернула два блока.
            lines = result.split("\n")
            filtered: list[str] = []
            for line in lines:
                low = line.lower()
                if filtered and ("цели" in low or "вызовы" in low):
                    break
                filtered.append(line)
            result = "\n".join(filtered).strip()

            # 2) Удаляем заголовок в начале строки вида "Ваши цели: ..." / "Цели - ..." и т.п.
            import re

            header_pattern = re.compile(
                r"^\s*(ваши\s+цели|цели|ваши\s+вызовы|вызовы)\s*[:\-–—]*\s*",
                flags=re.IGNORECASE,
            )
            result = header_pattern.sub("", result, count=1).strip()

            # 3) Проверяем, что результат не содержит намного больше информации, чем исходный текст
            # (Qwen не должен придумывать отсебятину)
            original_word_count = len(cleaned.split())
            result_word_count = len(result.split())
            
            # Если результат содержит в 3+ раза больше слов, чем исходный текст - подозрительно
            # Исключение: если исходный текст был очень коротким (1-2 слова), но результат разумный
            if original_word_count > 3 and result_word_count > original_word_count * 3:
                logger.warning(
                    f"Подозрение на выдуманные пункты: исходный текст ({original_word_count} слов): '{cleaned[:50]}...', "
                    f"результат ({result_word_count} слов): '{result[:100]}...'"
                )
                return f"[Не удалось разобрать текст: '{cleaned}'. Пожалуйста, напишите более подробно.]"

            if result:
                return result
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Не удалось получить форматирование от Qwen: %s", exc)

    return _fallback_format(cleaned)


@router.message(ProfileStates.waiting_for_challenges)
async def process_challenges(message: Message, state: FSMContext):
    """Обработчик текстовых сообщений для вызовов"""
    # Проверяем, что это текстовое сообщение
    if message.voice:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    challenges_text = message.text or (message.caption if message.caption else "")
    
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
            "Хочу изменить": "edit_profile_data",
            "Все верно": "confirm_profile_data"
        }
        review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
        await message.answer(review_text, reply_markup=review_keyboard)
    else:
        # Если целей еще нет, показываем только вызовы для проверки
        review_text = f"Ваши вызовы: {challenges}\n\nВсе верно?"
        review_buttons = {
            "Хочу изменить": "edit_profile_data",
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
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
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
        "Хочу изменить": "edit_profile_data",
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
        
        # Получаем все три времени для формирования сообщения
        def format_time(time_obj):
            if not time_obj:
                return "не установлено"
            # Убираем ведущий ноль из часов (9.00 вместо 09.00)
            hours = time_obj.hour
            minutes = time_obj.minute
            return f"{hours}.{minutes:02d}"
        
        morning_time = format_time(user.morning_notification_time)
        day_time = format_time(user.day_notification_time)
        evening_time = format_time(user.evening_notification_time)
        
        # Проверяем, все ли времена установлены (для первого визита)
        all_times_set = (
            user.morning_notification_time and
            user.day_notification_time and
            user.evening_notification_time
        )
        is_first_visit = user.is_first_visit
    finally:
        session.close()

    # Формируем новое сообщение с временами из БД
    confirmation = (
        "Спасибо! Время напоминаний изменено.\n"
        "Бот будет присылать вам сообщения:\n\n"
        f"Утром: в {morning_time}\n"
        f"Днем: в {day_time}\n"
        f"Вечером: в {evening_time}\n"
        "по московскому времени."
    )
    
    # Для первого визита, если все времена установлены, показываем "Продолжить"
    if is_first_visit and all_times_set:
        buttons = {
            "Продолжить": "continue_after_notification",
        }
    else:
        buttons = {
            "Настроить бота": "bot_settings",
            "В главное меню": "back_to_menu",
        }
    keyboard = await keyboard_ops.create_keyboard(buttons=buttons, interval=1)
    await message.answer(confirmation, reply_markup=keyboard)
    await state.clear()


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
            "Да": "username_confirm_yes",
            "Нет": "username_confirm_no"
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
        "Да": "username_confirm_yes",
        "Нет": "username_confirm_no"
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
        "Изменить данные": "edit_profile_personal_data",
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
        "Изменить данные": "edit_profile_personal_data",
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
        "Изменить данные": "edit_profile_personal_data",
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
        "Изменить данные": "edit_profile_personal_data",
        "Верно": "confirm_profile_personal_data"
    }
    review_keyboard = await keyboard_ops.create_keyboard(buttons=review_buttons, interval=2)
    await message.answer(review_text, reply_markup=review_keyboard)


# Обработчики стратсубботы должны быть зарегистрированы ДО общего обработчика текстовых сообщений
# чтобы они имели приоритет при обработке сообщений в состоянии стратсубботы
@router.message(SaturdayReflectionStates.answering_segment_1)
async def process_saturday_segment_1(message: Message, state: FSMContext):
    """Обработчик ответа на сегмент 1/5 (Похвастаться)."""
    logger.info(f"[SATURDAY] Обработчик segment_1 вызван для пользователя {message.from_user.id}")
    logger.info(f"[SATURDAY] Тип сообщения: text={message.text is not None}, voice={message.voice is not None}")
    
    next_question = (
        "2/5 Второй шаг — посмотреть на то, что не получилось 🔍\n"
        "Где ты застрял? В чём было ключевое противоречие недели? Какие ограничения встретились, что забирало энергию?\n"
        "Важно не просто пожаловаться, а конструктивно разобрать, где были сложности.\n\n"
        "✍️ Напиши или наговори свои наблюдения — мы добавим их в твою карту личной стратегии"
    )
    await _process_saturday_reflection_answer(
        message, state, 1,
        SaturdayReflectionStates.answering_segment_2,
        next_question
    )


@router.message(SaturdayReflectionStates.answering_segment_2)
async def process_saturday_segment_2(message: Message, state: FSMContext):
    """Обработчик ответа на сегмент 2/5 (Что не получилось)."""
    next_question = (
        "3/5 Третий шаг — поблагодарить 🙏\n"
        "Вспомни, кто помог тебе на этой неделе. Чья поддержка была особенно ценной? Кому хочется сказать спасибо?\n"
        "Для продвинутых: прямо сейчас можно взять телефон и отправить пару тёплых слов тем, о ком ты подумал. Благодарность — это практика, которая расширяет поле возможностей.\n\n"
        "✍️ Напиши или наговори свой ответ — он тоже войдёт в твою стратегию"
    )
    await _process_saturday_reflection_answer(
        message, state, 2,
        SaturdayReflectionStates.answering_segment_3,
        next_question
    )


@router.message(SaturdayReflectionStates.answering_segment_3)
async def process_saturday_segment_3(message: Message, state: FSMContext):
    """Обработчик ответа на сегмент 3/5 (Поблагодарить)."""
    next_question = (
        "4/5 Четвёртый шаг — помечтать ✨\n"
        "Вернись к большим целям и намерениям, которые ставил(а) в начале. Подумай: что из опыта этой недели хочется добавить в них? Какие новые инсайты и наблюдения стоит приземлить в твою личную стратегию?\n\n"
        "✍️ Поделись своими мыслями письменно или голосом"
    )
    await _process_saturday_reflection_answer(
        message, state, 3,
        SaturdayReflectionStates.answering_segment_4,
        next_question
    )


@router.message(SaturdayReflectionStates.answering_segment_4)
async def process_saturday_segment_4(message: Message, state: FSMContext):
    """Обработчик ответа на сегмент 4/5 (Помечтать)."""
    next_question = (
        "5/5 И пятый шаг — пообещать 💪\n"
        "Выбери один-два фокуса на следующую неделю. Это должны быть те самые «сдвиговые задачи», которые реально продвинут тебя к важным целям.\n\n"
        "✍️ Напиши или наговори, что берёшь в фокус. Мы сохраним это в твоей карте стратегии как твой следующий шаг"
    )
    await _process_saturday_reflection_answer(
        message, state, 4,
        SaturdayReflectionStates.answering_segment_5,
        next_question
    )


@router.message(SaturdayReflectionStates.answering_segment_5)
async def process_saturday_segment_5(message: Message, state: FSMContext):
    """Обработчик ответа на сегмент 5/5 (Пообещать)."""
    await _process_saturday_reflection_answer(
        message, state, 5,
        None,  # Нет следующего состояния
        ""  # Нет следующего вопроса
    )


@router.message(F.voice | F.text)
async def process_touch_question_answer(message: Message, state: FSMContext):
    """Обработчик ответов на вопросы касания (проверяет Redis для определения состояния)"""
    logger.info(f"[TOUCH_QUESTION] Проверяем Redis для определения состояния")
    
    # Сначала проверяем текущее состояние FSM
    current_fsm_state = await state.get_state()
    logger.info(f"[TOUCH_QUESTION] Текущее состояние FSM: {current_fsm_state}")
    
    if current_fsm_state:
        # Проверяем, не находится ли пользователь в состоянии стратсубботы
        if current_fsm_state.startswith("SaturdayReflectionStates:"):
            logger.info(f"[TOUCH_QUESTION] Пользователь в состоянии стратсубботы ({current_fsm_state}), пропускаем обработку касаний - даем возможность другим обработчикам обработать")
            # НЕ обрабатываем, чтобы дать возможность специфичным обработчикам состояний обработать сообщение
            return
        # Если состояние не TouchQuestionStates.waiting_for_answer, пропускаем
        if current_fsm_state != "TouchQuestionStates:waiting_for_answer":
            logger.info(f"[TOUCH_QUESTION] Состояние FSM не TouchQuestionStates.waiting_for_answer ({current_fsm_state}), пропускаем")
            return
    
    # Сначала проверяем, есть ли состояние в Redis
    try:
        import redis
        # from core.config import settings
        
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
        
        # Проверяем, не находится ли пользователь в состоянии стратсубботы
        saturday_states = [
            "SaturdayReflectionStates:answering_segment_1",
            "SaturdayReflectionStates:answering_segment_2",
            "SaturdayReflectionStates:answering_segment_3",
            "SaturdayReflectionStates:answering_segment_4",
            "SaturdayReflectionStates:answering_segment_5",
            "SaturdayReflectionStates:confirming_segment_1",
            "SaturdayReflectionStates:confirming_segment_2",
            "SaturdayReflectionStates:confirming_segment_3",
            "SaturdayReflectionStates:confirming_segment_4",
            "SaturdayReflectionStates:confirming_segment_5",
        ]
        
        if redis_state in saturday_states:
            logger.info(f"[TOUCH_QUESTION] Пользователь в состоянии стратсубботы ({redis_state}), пропускаем обработку касаний")
            return
        
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
        # from core.config import settings
        
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
            
            logger.info(f"[TOUCH_QUESTION] ===== ЗАГРУЗКА ДАННЫХ ИЗ REDIS (ГОЛОСОВОЕ) =====")
            logger.info(f"[TOUCH_QUESTION] Ключ Redis: {data_key}")
            logger.info(f"[TOUCH_QUESTION] Текущий индекс вопроса из Redis: {current_question_index_from_redis}")
            logger.info(f"[TOUCH_QUESTION] Всего вопросов: {len(questions_list_from_redis)}")
            if questions_list_from_redis and current_question_index_from_redis < len(questions_list_from_redis):
                logger.info(f"[TOUCH_QUESTION] Текущий вопрос (индекс {current_question_index_from_redis}): {questions_list_from_redis[current_question_index_from_redis]}")
            logger.info(f"[TOUCH_QUESTION] Список всех вопросов: {questions_list_from_redis}")
            logger.info(f"[TOUCH_QUESTION] =================================================")
            
            # Сохраняем в state для использования
            await state.update_data(
                touch_content_id=data.get("touch_content_id"),
                questions_list=questions_list_from_redis,
                current_question_index=current_question_index_from_redis,
                answers=data.get("answers", []),
                telegram_id=message.from_user.id  # Сохраняем telegram_id для использования при обновлении
            )
            logger.info(f"[TOUCH_QUESTION] Данные сохранены в state: questions_list={len(questions_list_from_redis)}, current_question_index={current_question_index_from_redis}, telegram_id={message.from_user.id}")
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
            "Хочу перезаписать": "touch_voice_rerecord",
            "Фиксируем": "touch_voice_confirm"
        }
        keyboard = await keyboard_ops.create_keyboard(buttons=keyboard_buttons, interval=2)
        
        confirm_text = get_booking_text("touch_voice_confirm_prompt")
        await message.answer(confirm_text, reply_markup=keyboard)
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
                    touch_content_id=data.get("touch_content_id"),
                    reflection_mode=data.get("reflection_mode", False),
                    telegram_id=message.from_user.id  # Сохраняем telegram_id для использования при обновлении
                )
            else:
                logger.warning(f"[TOUCH_QUESTION] Данные не найдены в Redis по ключу {data_key}")
                # Пробуем найти все ключи с этим пользователем
                pattern = f"fsm:*:{telegram_id}:data"
                all_keys = redis_client.keys(pattern)
                logger.info(f"[TOUCH_QUESTION] Найдены ключи Redis для пользователя {telegram_id}: {all_keys}")
        except Exception as e:
            logger.error(f"[TOUCH_QUESTION] Ошибка при загрузке данных из Redis: {e}", exc_info=True)
    
    # Проверяем, не в режиме ли рефлексии без вопросов
    reflection_mode = data.get("reflection_mode", False)
    if not questions_list:
        if reflection_mode:
            # Пользователь отправил ответ на рефлексию, а вопросов нет
            logger.info(f"[TOUCH_QUESTION] Ответ на рефлексию без вопросов получен: {answer_text[:200]}...")
            
            # Сохраняем ответ на рефлексию в БД
            try:
                session = next(get_session())
                try:
                    user_repo = UserRepository(session)
                    user = user_repo.get_by_telegram_id(message.from_user.id)
                    
                    if user:
                        reflection_repo = EveningReflectionRepository(session)
                        reflection_date = date.today()
                        
                        reflection_repo.create_or_update(
                            user_id=user.id,
                            reflection_date=reflection_date,
                            reflection_text=answer_text,
                        )
                        logger.info(f"[EVENING_REFLECTION] Сохранена вечерняя рефлексия для пользователя {user.id}")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"[EVENING_REFLECTION] Ошибка при сохранении вечерней рефлексии в БД: {e}", exc_info=True)
            
            # Отправляем благодарность и главное меню
            await message.answer("Спасибо! Твоя рефлексия сохранена. Это поможет сформировать твою мини-стратегию.")
            
            # Очищаем состояние
            await state.clear()
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
                data_key = f"fsm:{bot_id}:{telegram_id}:data"
                redis_client.delete(state_key, data_key)
                logger.info(f"[TOUCH_QUESTION] Данные очищены из Redis для пользователя {telegram_id}")
            except Exception as e:
                logger.error(f"[TOUCH_QUESTION] Ошибка при очистке данных из Redis: {e}", exc_info=True)
            
            # Отправляем главное меню
            step_6_text = get_booking_text("step_6")
            menu_keyboard = await keyboard_ops.create_keyboard(
                buttons={
                    "Обратная связь": "feedback",
                    "О боте": "about_bot",
                    "Стратегия дня": "day_strategy",
                    "Настройка бота": "bot_settings",
                    "Моя подписка": "my_subscription",
                },
                interval=2,
            )
            await message.answer(step_6_text, reply_markup=menu_keyboard)
            return
        else:
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
    logger.info(f"[TOUCH_QUESTION] Текст ответа пользователя: {answer_text[:200]}...")
    
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
            f"ВАЖНО: Пользователь отвечал именно на вопрос #{question_number} '{current_question}', не путай с другими вопросами."
        )
        
        logger.info(f"[TOUCH_QUESTION] ===== ОТПРАВКА В QWEN =====")
        logger.info(f"[TOUCH_QUESTION] Вопрос #{question_number} (индекс {current_question_index}): {current_question}")
        logger.info(f"[TOUCH_QUESTION] Ответ пользователя: {answer_text}")
        logger.info(f"[TOUCH_QUESTION] Полный промпт для Qwen (первые 500 символов): {validation_prompt[:500]}...")
        logger.info(f"[TOUCH_QUESTION] ============================")
        
        logger.info(f"[TOUCH_QUESTION] Отправляем ответ в Qwen для валидации")
        validation_result = await generate_qwen_response(validation_prompt)
        logger.info(f"[TOUCH_QUESTION] Получено резюме от Qwen (длина: {len(validation_result) if validation_result else 0}): {validation_result[:200] if validation_result else 'None'}...")
        
        # Проверяем, что ответ не пустой
        if not validation_result or not validation_result.strip():
            logger.warning(f"[TOUCH_QUESTION] Qwen вернул пустой ответ, используем fallback")
            validation_result = "Ответ получен и сохранён."
        
        # Удаляем промежуточное сообщение
        try:
            await validation_msg.delete()
            logger.info(f"[TOUCH_QUESTION] Промежуточное сообщение удалено")
        except Exception as del_exc:
            logger.warning(f"[TOUCH_QUESTION] Не удалось удалить промежуточное сообщение: {del_exc}")
        
        # Показываем резюме пользователю
        try:
            logger.info(f"[TOUCH_QUESTION] Отправляем резюме пользователю (длина текста: {len(validation_result)})")
            await message.answer(f"📝 Резюме по вашему ответу:\n\n{validation_result}")
            logger.info(f"[TOUCH_QUESTION] ✓ Резюме успешно отправлено пользователю")
        except Exception as send_exc:
            logger.error(f"[TOUCH_QUESTION] ✗ Ошибка при отправке резюме пользователю: {send_exc}", exc_info=True)
            # Пробуем отправить хотя бы уведомление
            try:
                await message.answer("📝 Ваш ответ проанализирован и сохранён.")
            except:
                pass
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
        # from core.config import settings
        
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
            
            # Проверяем, что telegram_id не равен bot_id (это было бы ошибкой)
            if telegram_id == bot_id:
                logger.error(f"[TOUCH_QUESTION] ОШИБКА: telegram_id ({telegram_id}) равен bot_id ({bot_id})! Это неправильно!")
                # Пробуем получить telegram_id из state или из предыдущих данных
                telegram_id_from_data = data.get("telegram_id")
                if telegram_id_from_data and telegram_id_from_data != bot_id:
                    logger.warning(f"[TOUCH_QUESTION] Используем telegram_id из данных: {telegram_id_from_data}")
                    telegram_id = telegram_id_from_data
                else:
                    logger.error(f"[TOUCH_QUESTION] Не удалось найти правильный telegram_id! Используем message.from_user.id, но это может быть ошибкой.")
            
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            
            # Обновляем данные в Redis с новым индексом
            redis_data_to_save = {
                "touch_content_id": data.get("touch_content_id"),
                "questions_list": questions_list,
                "current_question_index": next_question_index,
                "answers": answers,
                "telegram_id": telegram_id  # Сохраняем telegram_id для проверки
            }
            logger.info(f"[TOUCH_QUESTION] ===== ОБНОВЛЕНИЕ ИНДЕКСА В REDIS =====")
            logger.info(f"[TOUCH_QUESTION] bot_id: {bot_id}, telegram_id: {telegram_id}")
            logger.info(f"[TOUCH_QUESTION] Ключ Redis: {data_key}")
            logger.info(f"[TOUCH_QUESTION] Старый индекс: {current_question_index}, новый индекс: {next_question_index}")
            logger.info(f"[TOUCH_QUESTION] Данные для сохранения: current_question_index={next_question_index}, questions_list={len(questions_list)}")
            redis_client.set(data_key, json.dumps(redis_data_to_save), ex=3600)
            logger.info(f"[TOUCH_QUESTION] Обновлен индекс в Redis: {next_question_index} (вопрос #{next_question_index + 1})")
            
            # Проверяем, что данные сохранились правильно
            saved_data_raw = redis_client.get(data_key)
            if saved_data_raw:
                saved_data = json.loads(saved_data_raw)
                saved_index = saved_data.get('current_question_index')
                logger.info(f"[TOUCH_QUESTION] Проверка: сохраненный индекс в Redis = {saved_index}")
                logger.info(f"[TOUCH_QUESTION] Проверка: сохраненный список вопросов = {saved_data.get('questions_list', [])}")
                if saved_index != next_question_index:
                    logger.error(f"[TOUCH_QUESTION] ОШИБКА: Индекс не совпадает! Ожидалось: {next_question_index}, получено: {saved_index}")
            else:
                logger.error(f"[TOUCH_QUESTION] ОШИБКА: Данные не найдены в Redis после сохранения!")
            logger.info(f"[TOUCH_QUESTION] ======================================")
        except Exception as e:
            logger.error(f"[TOUCH_QUESTION] Ошибка при обновлении индекса в Redis: {e}", exc_info=True)
    else:
        # Все вопросы отвечены
        # Получаем telegram_id до очистки состояния
        bot_id = message.bot.id
        telegram_id = message.from_user.id
        
        # Проверяем, что telegram_id не равен bot_id
        telegram_id_from_data = data.get("telegram_id")
        if telegram_id == bot_id and telegram_id_from_data and telegram_id_from_data != bot_id:
            telegram_id = telegram_id_from_data
        
        # Сохраняем ответы в БД перед очисткой состояния
        touch_content_id = data.get("touch_content_id")
        if touch_content_id and answers:
            try:
                session = next(get_session())
                try:
                    user_repo = UserRepository(session)
                    user = user_repo.get_by_telegram_id(telegram_id)
                    
                    if user:
                        # Проверяем, что touch_content существует
                        touch_content_repo = TouchContentRepository(session)
                        touch_content = touch_content_repo.get_by_id(touch_content_id)
                        
                        if touch_content:
                            answer_repo = TouchAnswerRepository(session)
                            touch_date = date.today()
                            
                            # Сохраняем все ответы
                            answer_repo.create_answers(
                                user_id=user.id,
                                touch_content_id=touch_content_id,
                                touch_date=touch_date,
                                answers=answers,
                            )
                            logger.info(
                                f"[TOUCH_ANSWER] Сохранены ответы для пользователя {user.id}, "
                                f"touch_content_id={touch_content_id}, touch_type={touch_content.touch_type}, "
                                f"количество ответов={len(answers)}"
                            )
                        else:
                            logger.warning(f"[TOUCH_ANSWER] TouchContent с id={touch_content_id} не найден")
                finally:
                    session.close()
            except Exception as e:
                logger.error(f"[TOUCH_ANSWER] Ошибка при сохранении ответов в БД: {e}", exc_info=True)
        
        saved_text = get_booking_text("touch_answers_saved")
        await message.answer(saved_text)
        
        # Отправляем сообщение с кнопками
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from core.config import settings
        
        keyboard_builder = InlineKeyboardBuilder()
        
        # Кнопка "Перейти в чат"
        if settings.community_chat_url:
            keyboard_builder.button(text="Перейти в чат", url=settings.community_chat_url)
        else:
            keyboard_builder.button(text="Перейти в чат", callback_data="chat_placeholder")
        
        # Кнопка "Продолжить"
        keyboard_builder.button(text="Продолжить", callback_data="touch_questions_continue")
        keyboard_builder.adjust(1, 1)
        keyboard = keyboard_builder.as_markup()
        
        chat_invitation_text = get_booking_text("touch_chat_invitation")
        await message.answer(chat_invitation_text, reply_markup=keyboard)
        
        # Очищаем состояние и данные из Redis после завершения всех вопросов
        await state.clear()
        
        # Очищаем данные из Redis
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
            
            state_key = f"fsm:{bot_id}:{telegram_id}:state"
            data_key = f"fsm:{bot_id}:{telegram_id}:data"
            
            # Очищаем данные из Redis
            redis_client.delete(state_key, data_key)
            logger.info(f"[TOUCH_QUESTION] Данные очищены из Redis для пользователя {telegram_id} после завершения вопросов")
        except Exception as e:
            logger.error(f"[TOUCH_QUESTION] Ошибка при очистке данных из Redis: {e}", exc_info=True)


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
        # from core.config import settings
        
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


async def _process_saturday_reflection_answer(
    message: Message,
    state: FSMContext,
    current_segment: int,
    next_state: SaturdayReflectionStates | None,
    next_question: str
) -> None:
    """Обработать ответ на сегмент рефлексии стратсубботы."""
    logger.info(f"[SATURDAY] _process_saturday_reflection_answer вызван для сегмента {current_segment}")
    processing_msg = None
    
    try:
        # Извлекаем текст (голосовое или текстовое)
        if message.voice:
            logger.info("[SATURDAY] Получено голосовое сообщение, начинаем транскрипцию...")
            processing_msg = await message.answer("🔄 Обрабатываю голосовое сообщение...")
            
            file = await message.bot.get_file(message.voice.file_id)
            audio_data = BytesIO()
            await message.bot.download_file(file.file_path, destination=audio_data)
            raw_text = await transcribe_audio(audio_data)
            
            if processing_msg:
                try:
                    await processing_msg.delete()
                except:
                    pass
        elif message.text:
            raw_text = message.text.strip()
        else:
            await message.answer("Пожалуйста, отправьте текстовое сообщение.")
            return
        
        if not raw_text or not raw_text.strip():
            await message.answer("Пожалуйста, отправьте текстовое сообщение.")
            return
        
        # Отправляем в Qwen для обработки
        processing_msg = await message.answer("🔄 Обрабатываю ваш ответ...")
        
        qwen_prompt = (
            f"Исходный текст пользователя:\n{raw_text}\n\n"
            "Исправь орфографию и пунктуацию, скомпонуй текст так, чтобы он был читаемым и структурированным. "
            "ВАЖНО: НЕ добавляй ничего от себя, НЕ интерпретируй, НЕ додумывай. "
            "Верни ТОЛЬКО исправленный и скомпонованный текст того, что сказал пользователь. "
            "Сохрани смысл и содержание, но улучши форму."
        )
        
        processed_text = await generate_qwen_response(qwen_prompt)
        
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        
        if not processed_text or not processed_text.strip():
            processed_text = raw_text  # Используем исходный текст, если Qwen не ответил
        
        # Сохраняем обработанный текст во временное хранилище для подтверждения
        await state.update_data(
            temp_processed_text=processed_text.strip(),
            temp_current_segment=current_segment,
            temp_next_question=next_question
        )
        
        # Показываем обработанный текст для подтверждения
        confirmation_text = f"📝 Вот как мы обработали ваш ответ:\n\n{processed_text.strip()}\n\nВсё верно?"
        
        # Создаем клавиатуру с кнопками подтверждения
        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.button(text="✅ Все верно", callback_data=f"saturday_confirm_{current_segment}")
        keyboard_builder.button(text="✏️ Изменить", callback_data=f"saturday_edit_{current_segment}")
        keyboard_builder.adjust(2)
        keyboard = keyboard_builder.as_markup()
        
        # Определяем состояние подтверждения
        confirmation_states = {
            1: SaturdayReflectionStates.confirming_segment_1,
            2: SaturdayReflectionStates.confirming_segment_2,
            3: SaturdayReflectionStates.confirming_segment_3,
            4: SaturdayReflectionStates.confirming_segment_4,
            5: SaturdayReflectionStates.confirming_segment_5,
        }
        
        await message.answer(confirmation_text, reply_markup=keyboard)
        await state.set_state(confirmation_states[current_segment])
            
    except TimeoutError:
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        await message.answer("Сервер обрабатывает сообщение слишком долго. Попробуйте отправить более короткое сообщение или повторите попытку позже.")
    except Exception as e:
        logger.error(f"[SATURDAY] Ошибка при обработке ответа: {e}", exc_info=True)
        if processing_msg:
            try:
                await processing_msg.delete()
            except:
                pass
        await message.answer("Произошла ошибка при обработке ответа. Попробуйте отправить сообщение заново.")

