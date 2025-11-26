"""Обработчики для вечерней оценки"""
import logging
import json
import redis
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.config import settings
from core.states import EveningRatingStates
from datetime import date
from database.session import get_session
from repositories.user_repository import UserRepository
from repositories.evening_rating_repository import EveningRatingRepository

router = Router()
logger = logging.getLogger(__name__)


async def _handle_rating_energy(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос 1/5: Оценка уровня энергии."""
    rating_value = int(callback.data.replace("evening_rating_", ""))
    
    await _save_rating_and_send_next(
        callback,
        state,
        rating_value,
        current_question=1,
        next_question_text="По шкале от 1 до 10 оцени уровень счастья в деятельности сегодня",
        next_state=EveningRatingStates.rating_happiness,
        next_state_name="rating_happiness",
        rating_key="rating_energy"
    )


async def _handle_rating_happiness(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос 2/5: Оценка уровня счастья."""
    rating_value = int(callback.data.replace("evening_rating_", ""))
    
    await _save_rating_and_send_next(
        callback,
        state,
        rating_value,
        current_question=2,
        next_question_text="По шкале от 1 до 10 оцени, насколько сегодня ты продвинулся к своим значимым результатам",
        next_state=EveningRatingStates.rating_progress,
        next_state_name="rating_progress",
        rating_key="rating_happiness"
    )


async def _handle_rating_progress(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос 3/5: Оценка продвижения к результату/целям курса."""
    rating_value = int(callback.data.replace("evening_rating_", ""))
    
    bot_id = callback.bot.id
    telegram_id = callback.from_user.id
    
    redis_client = _get_redis_client()
    state_key = f"fsm:{bot_id}:{telegram_id}:state"
    data_key = f"fsm:{bot_id}:{telegram_id}:data"
    
    # Загружаем данные из Redis
    redis_data_raw = redis_client.get(data_key)
    if redis_data_raw:
        redis_data = json.loads(redis_data_raw)
    else:
        redis_data = {}
    
    # Сохраняем текущую оценку
    redis_data["rating_progress"] = rating_value
    
    # Сохраняем обратно в Redis
    redis_client.set(data_key, json.dumps(redis_data), ex=3600)
    
    # Сохраняем в БД
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_by_telegram_id(telegram_id)
        if user:
            rating_repo = EveningRatingRepository(session)
            rating_date = date.today()
            
            # Получаем все оценки из Redis
            rating_energy = redis_data.get('rating_energy')
            rating_happiness = redis_data.get('rating_happiness')
            
            # Если все оценки есть, сохраняем
            if rating_energy is not None and rating_happiness is not None:
                rating_repo.create_or_update(
                    user_id=user.id,
                    rating_date=rating_date,
                    rating_energy=rating_energy,
                    rating_happiness=rating_happiness,
                    rating_progress=rating_value,
                )
                logger.info(f"[EVENING_RATING] Сохранены оценки для пользователя {user.id}: энергия={rating_energy}, счастье={rating_happiness}, прогресс={rating_value}")
            else:
                logger.warning(f"[EVENING_RATING] Не все оценки получены для пользователя {user.id}, сохраняем только прогресс")
    finally:
        session.close()
    
    await callback.answer(f"Вы выбрали: {rating_value}")
    
    # Отправляем сообщение о рефлексии
    reflection_text = "Вечерняя рефлексия - одна из самых важных практик каждого дня! Мы учимся осознанному разбору и анализу прожитого опыта.  Пожалуйста, подробно ответь на вопросы ниже - письменно или голосовым сообщением. Бот соберет ключевые мысли в твою личную стратегию."
    await callback.message.answer(reflection_text)
    
    # Получаем touch_content_id и отправляем вопросы из админки
    touch_content_id = redis_data.get("touch_content_id")
    if touch_content_id:
        await _send_evening_questions(callback.bot, telegram_id, bot_id, touch_content_id, redis_client, state)
    else:
        logger.warning(f"[EVENING_RATING] touch_content_id не найден в Redis для пользователя {telegram_id}")
        # Если нет touch_content_id, просто очищаем состояние
        redis_client.delete(state_key, data_key)
        await state.clear()
    
    # Если вопросы не были отправлены, всё равно устанавливаем состояние для обработки ответа на рефлексию
    # Проверяем, изменилось ли состояние (если нет - значит вопросы не найдены)
    current_state = redis_client.get(state_key)
    if current_state and current_state == "EveningRatingStates:rating_progress":
        # Вопросы не были отправлены, устанавливаем состояние для обработки рефлексии
        from core.states import TouchQuestionStates
        redis_client.set(state_key, "TouchQuestionStates:waiting_for_answer", ex=3600)
        redis_data["reflection_mode"] = True  # Флаг, что мы ожидаем ответ на рефлексию без вопросов
        redis_client.set(data_key, json.dumps(redis_data), ex=3600)
        await state.set_state(TouchQuestionStates.waiting_for_answer)
        logger.info(f"[EVENING_RATING] Вопросы не найдены, устанавливаем состояние для обработки рефлексии")


async def _send_evening_questions(bot, telegram_id: int, bot_id: int, touch_content_id: int, redis_client, state: FSMContext) -> None:
    """Отправить вопросы из админки для вечернего касания."""
    from database.session import SessionLocal
    from repositories.touch_content_repository import TouchContentRepository
    from core.states import TouchQuestionStates
    
    # Получаем touch_content из БД
    with SessionLocal() as session:
        repo = TouchContentRepository(session)
        touch_content = repo.get_by_id(touch_content_id)
    
    if not touch_content or not touch_content.questions:
        logger.warning(f"[EVENING_RATING] Вопросы не найдены для touch_content_id={touch_content_id}")
        return
    
    # Разделяем вопросы по переносу строки
    questions_text = touch_content.questions.strip()
    split_lines = questions_text.split('\n')
    questions_list = [line.strip() for line in split_lines if line.strip()]
    
    if not questions_list:
        logger.warning(f"[EVENING_RATING] Список вопросов пуст после разделения")
        return
    
    # Отправляем первый вопрос
    first_question = questions_list[0]
    await bot.send_message(telegram_id, first_question)
    
    # Сохраняем состояние и данные в Redis для обработки ответов
    state_key = f"fsm:{bot_id}:{telegram_id}:state"
    data_key = f"fsm:{bot_id}:{telegram_id}:data"
    
    # Сохраняем состояние для обработки вопросов касания
    redis_client.set(state_key, "TouchQuestionStates:waiting_for_answer", ex=3600)
    
    # Сохраняем данные о вопросах
    redis_data = {
        "touch_content_id": touch_content_id,
        "questions_list": questions_list,
        "current_question_index": 0,
        "answers": []
    }
    redis_client.set(data_key, json.dumps(redis_data), ex=3600)
    
    # Устанавливаем состояние в FSM
    await state.set_state(TouchQuestionStates.waiting_for_answer)
    await state.update_data(
        touch_content_id=touch_content_id,
        questions_list=questions_list,
        current_question_index=0,
        answers=[]
    )
    
    logger.info(f"[EVENING_RATING] Отправлен первый вопрос из админки, всего вопросов: {len(questions_list)}")


@router.callback_query(F.data.startswith("evening_rating_"))
async def callback_evening_rating_check_state(callback: CallbackQuery, state: FSMContext):
    """Проверяет состояние в Redis и перенаправляет на соответствующий обработчик."""
    bot_id = callback.bot.id
    telegram_id = callback.from_user.id
    
    redis_client = _get_redis_client()
    state_key = f"fsm:{bot_id}:{telegram_id}:state"
    redis_state = redis_client.get(state_key)
    
    logger.info(f"[EVENING_RATING] Проверяем Redis для определения состояния: {redis_state}")
    
    # Если состояние не найдено в Redis, пропускаем
    if not redis_state:
        logger.info(f"[EVENING_RATING] Состояние не найдено в Redis, пропускаем")
        return
    
    # Устанавливаем состояние в FSM на основе Redis и вызываем соответствующий обработчик
    if redis_state == "EveningRatingStates:rating_energy":
        await state.set_state(EveningRatingStates.rating_energy)
        await _handle_rating_energy(callback, state)
    elif redis_state == "EveningRatingStates:rating_happiness":
        await state.set_state(EveningRatingStates.rating_happiness)
        await _handle_rating_happiness(callback, state)
    elif redis_state == "EveningRatingStates:rating_progress":
        await state.set_state(EveningRatingStates.rating_progress)
        await _handle_rating_progress(callback, state)
    else:
        logger.warning(f"[EVENING_RATING] Неизвестное состояние в Redis: {redis_state}")


def _create_rating_keyboard():
    """Создает клавиатуру с кнопками 1-10 для оценки."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"evening_rating_{i}")
    builder.adjust(5, 5)  # 2 ряда по 5 кнопок
    return builder.as_markup()


def _get_redis_client():
    """Получить клиент Redis."""
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=settings.redis_db,
        decode_responses=True
    )


async def _save_rating_and_send_next(
    callback: CallbackQuery,
    state: FSMContext,
    rating_value: int,
    current_question: int,
    next_question_text: str,
    next_state: EveningRatingStates,
    next_state_name: str,
    rating_key: str
) -> None:
    """Сохранить оценку и отправить следующий вопрос."""
    bot_id = callback.bot.id
    telegram_id = callback.from_user.id
    
    redis_client = _get_redis_client()
    state_key = f"fsm:{bot_id}:{telegram_id}:state"
    data_key = f"fsm:{bot_id}:{telegram_id}:data"
    
    # Загружаем данные из Redis
    redis_data_raw = redis_client.get(data_key)
    if redis_data_raw:
        redis_data = json.loads(redis_data_raw)
    else:
        redis_data = {
            "rating_energy": None,
            "rating_happiness": None,
            "rating_progress": None,
            "rating_question_4": None,
            "rating_question_5": None,
            "current_question": current_question
        }
    
    # Сохраняем текущую оценку
    redis_data[rating_key] = rating_value
    redis_data["current_question"] = current_question + 1
    
    # Сохраняем обратно в Redis
    redis_client.set(data_key, json.dumps(redis_data), ex=3600)
    redis_client.set(state_key, f"EveningRatingStates:{next_state_name}", ex=3600)
    
    # Устанавливаем состояние в FSM
    await state.set_state(next_state)
    
    # Отправляем следующий вопрос
    keyboard = _create_rating_keyboard()
    await callback.message.answer(next_question_text, reply_markup=keyboard)
    await callback.answer(f"Вы выбрали: {rating_value}")



