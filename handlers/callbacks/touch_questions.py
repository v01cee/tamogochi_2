from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from io import BytesIO

from core.keyboards import KeyboardOperations
from core.states import TouchQuestionStates
from whisper_client import transcribe_audio
import logging

router = Router()
keyboard_ops = KeyboardOperations()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "touch_voice_rerecord")
async def callback_touch_voice_rerecord(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Перезаписать' для голосового сообщения"""
    await callback.answer()
    await callback.message.delete()
    
    # Возвращаемся в состояние ожидания ответа
    await state.set_state(TouchQuestionStates.waiting_for_answer)
    await callback.message.answer("Запишите голосовое сообщение заново.")


@router.callback_query(F.data == "touch_voice_confirm")
async def callback_touch_voice_confirm(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Фиксируем' для голосового сообщения"""
    await callback.answer()
    
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
        
        bot_id = callback.bot.id
        telegram_id = callback.from_user.id
        data_key = f"fsm:{bot_id}:{telegram_id}:data"
        
        # Загружаем данные из Redis
        redis_data = redis_client.get(data_key)
        if redis_data:
            logger.info(f"[TOUCH_QUESTION] Загружаем данные из Redis в callback")
            data = json.loads(redis_data)
            # Сохраняем в state для использования
            await state.update_data(
                touch_content_id=data.get("touch_content_id"),
                questions_list=data.get("questions_list", []),
                current_question_index=data.get("current_question_index", 0),
                answers=data.get("answers", [])
            )
            logger.info(f"[TOUCH_QUESTION] Данные загружены в callback: questions_list={len(data.get('questions_list', []))}")
    except Exception as e:
        logger.error(f"[TOUCH_QUESTION] Ошибка при загрузке данных из Redis в callback: {e}", exc_info=True)
    
    # Получаем file_id голосового сообщения из state
    data = await state.get_data()
    voice_file_id = data.get("voice_file_id")
    
    if not voice_file_id:
        await callback.message.answer("Ошибка: не найдено голосовое сообщение. Попробуйте отправить заново.")
        await state.set_state(TouchQuestionStates.waiting_for_answer)
        return
    
    # Удаляем сообщение с кнопками
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем, что обрабатываем
    processing_msg = await callback.message.answer("🔄 Обрабатываю голосовое сообщение...")
    
    try:
        # Скачиваем голосовое сообщение
        file = await callback.bot.get_file(voice_file_id)
        audio_data = BytesIO()
        await callback.bot.download_file(file.file_path, destination=audio_data)
        
        # Расшифровываем через Whisper
        logger.info(f"[TOUCH_QUESTION] Расшифровываем голосовое сообщение")
        answer_text = await transcribe_audio(audio_data)
        
        if not answer_text or not answer_text.strip():
            await processing_msg.delete()
            await callback.message.answer("Не удалось распознать речь в голосовом сообщении. Попробуйте записать заново.")
            await state.set_state(TouchQuestionStates.waiting_for_answer)
            return
        
        logger.info(f"[TOUCH_QUESTION] Расшифрованный текст: {answer_text}")
        
        # Удаляем промежуточное сообщение
        try:
            await processing_msg.delete()
        except:
            pass
        
        # Обрабатываем ответ с валидацией
        from handlers.start import _process_answer_with_validation
        await _process_answer_with_validation(callback.message, state, answer_text)
        
    except Exception as e:
        logger.error(f"[TOUCH_QUESTION] Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        try:
            await processing_msg.delete()
        except:
            pass
        await callback.message.answer("Произошла ошибка при обработке голосового сообщения. Попробуйте отправить текстовое сообщение или повторите попытку позже.")
        await state.set_state(TouchQuestionStates.waiting_for_answer)

