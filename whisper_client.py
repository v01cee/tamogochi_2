"""
Клиент для работы с Whisper API на Cloud.ru.
Обрабатывает авторизацию и транскрипцию аудио.
"""
import os
import base64
import logging
from io import BytesIO
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем конфигурацию из переменных окружения
CLOUDRU_IAM_KEY = os.getenv('CLOUDRU_IAM_KEY')
CLOUDRU_IAM_SECRET = os.getenv('CLOUDRU_IAM_SECRET')
MODEL_URL = os.getenv('MODEL_URL')
MODEL_NAME = os.getenv('MODEL_NAME', 'model-run-wxryh-soft')  # Имя модели по умолчанию

# Проверяем наличие обязательных переменных для работы с API
if not all([CLOUDRU_IAM_KEY, CLOUDRU_IAM_SECRET, MODEL_URL]):
    logger.warning("Не все переменные окружения для Cloud.ru API установлены. Проверьте .env файл")


async def get_bearer_token() -> str:
    """
    Получает Bearer токен через OAuth2 client_credentials flow для Cloud.ru API.
    Согласно документации Cloud.ru, нужно сначала получить токен, затем использовать его.
    
    Returns:
        Bearer токен для авторизации запросов
    """
    try:
        token_url = "https://auth.iam.sbercloud.ru/auth/system/openid/token"
        
        # Параметры для OAuth2 client_credentials flow
        data = {
            'grant_type': 'client_credentials',
            'client_id': CLOUDRU_IAM_KEY,
            'client_secret': CLOUDRU_IAM_SECRET
        }
        
        response = requests.post(
            token_url,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            access_token = result.get('access_token')
            if access_token:
                logger.info("Успешно получен Bearer токен")
                return access_token
            else:
                raise ValueError(f"Токен не найден в ответе: {result}")
        else:
            raise Exception(f"Ошибка при получении токена: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Ошибка при получении Bearer токена: {e}", exc_info=True)
        raise


async def get_auth_headers(url: str = "", method: str = "POST") -> dict:
    """
    Получает заголовки авторизации с Bearer токеном для Cloud.ru API.
    Согласно документации, нужно использовать Bearer токен, полученный через OAuth2.
    
    Args:
        url: URL запроса (не используется, но оставлен для совместимости)
        method: HTTP метод (не используется, но оставлен для совместимости)
    
    Returns:
        Словарь с заголовками для авторизации
    """
    headers = {}
    
    try:
        # Получаем Bearer токен через OAuth2
        bearer_token = await get_bearer_token()
        headers['Authorization'] = f'Bearer {bearer_token}'
        headers['accept'] = 'application/json'
        
    except Exception as e:
        logger.error(f"Не удалось получить Bearer токен: {e}")
        # Fallback: пробуем Basic Auth (на случай, если токен не нужен)
        if CLOUDRU_IAM_KEY and CLOUDRU_IAM_SECRET:
            credentials = f"{CLOUDRU_IAM_KEY}:{CLOUDRU_IAM_SECRET}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f'Basic {encoded_credentials}'
    
    return headers


async def transcribe_via_direct_http(audio_data: bytes) -> str:
    """
    Прямой HTTP запрос к Whisper API через endpoint.
    Использует OAuth2 Bearer токен для авторизации согласно документации Cloud.ru.
    
    Args:
        audio_data: Байты аудио файла
        
    Returns:
        Транскрибированный текст
    """
    try:
        # Согласно документации OpenAI, Whisper использует endpoint /v1/audio/transcriptions
        transcription_url = f"{MODEL_URL.rstrip('/')}/v1/audio/transcriptions"
        
        # Подготовка данных для multipart/form-data
        files = {
            'file': ('audio.ogg', audio_data, 'audio/ogg')
        }
        data = {
            'model': MODEL_NAME,  # Имя развернутой модели на Cloud.ru
            'language': 'ru',  # Язык транскрипции (можно убрать для автоопределения)
            'response_format': 'json'
        }
        
        # Получаем заголовки авторизации с Bearer токеном
        auth_headers = await get_auth_headers(transcription_url, 'POST')
        
        # Отправляем запрос с правильными заголовками
        logger.info(f"Отправляем запрос к {transcription_url}")
        logger.debug(f"Заголовки: {auth_headers}")
        response = requests.post(
            transcription_url,
            files=files,
            data=data,
            headers=auth_headers,
            timeout=60
        )
        
        logger.info(f"Получен ответ со статусом {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            text = result.get('text', '')
            if text:
                logger.info("Успешно получена транскрипция")
                return text
            else:
                # Логируем полный ответ для отладки
                logger.warning(f"Текст не найден в ответе. Полный ответ: {result}")
                raise ValueError(f"Текст не найден в ответе: {result}")
        else:
            # Логируем детали ошибки для отладки
            try:
                error_detail = response.json()
                logger.error(f"Ошибка API (status {response.status_code}): {error_detail}")
            except:
                logger.error(f"Ошибка API (status {response.status_code}): {response.text}")

            
    except Exception as e:
        logger.error(f"Ошибка при прямом HTTP запросе: {e}", exc_info=True)
        raise



async def transcribe_audio(audio_file: BytesIO) -> str:
    """
    Отправляет аудио файл на Whisper API для транскрипции.
    
    Args:
        audio_file: BytesIO объект с аудио данными
        
    Returns:
        Транскрибированный текст
    """
    try:
        audio_file.seek(0)
        audio_data = audio_file.read()
        
        # Используем прямой HTTP запрос к правильному endpoint
        return await transcribe_via_direct_http(audio_data)
            
    except Exception as e:
        logger.error(f"Ошибка при транскрипции: {e}", exc_info=True)
        raise

