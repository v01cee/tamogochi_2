"""
Клиент для работы с Whisper API на Cloud.ru.
Обрабатывает авторизацию и транскрипцию аудио.
"""
import base64
import glob
import logging
import os
import shutil
import time
import warnings
from io import BytesIO
import requests
from core.config import settings

# Подавляем предупреждение pydub о ffmpeg при импорте (проверим позже в optimize_audio)
warnings.filterwarnings("ignore", message=".*ffmpeg.*", category=RuntimeWarning)

# Настройка логирования
logger = logging.getLogger(__name__)

# Попытка импортировать pydub для оптимизации аудио
PYDUB_AVAILABLE = False
_AUDIO_SEGMENT = None
_PYDUB_ERROR = None

try:
    from pydub import AudioSegment
    
    # Пытаемся найти ffmpeg в стандартных местах Windows
    ffmpeg_path = None
    ffprobe_path = None
    
    # Сначала проверяем PATH
    ffmpeg_in_path = shutil.which("ffmpeg")
    ffprobe_in_path = shutil.which("ffprobe")
    
    if ffmpeg_in_path:
        ffmpeg_path = ffmpeg_in_path
        logger.info(f"ffmpeg найден в PATH: {ffmpeg_path}")
        # Ищем ffprobe в той же директории
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        ffprobe_candidate = os.path.join(ffmpeg_dir, "ffprobe.exe")
        if os.path.exists(ffprobe_candidate):
            ffprobe_path = ffprobe_candidate
            logger.info(f"ffprobe найден: {ffprobe_path}")
        elif ffprobe_in_path:
            ffprobe_path = ffprobe_in_path
            logger.info(f"ffprobe найден в PATH: {ffprobe_path}")
    else:
        # Ищем в стандартных местах
        possible_paths = [
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages"),
        ]
        
        # Также ищем через winget (может быть в разных местах)
        winget_base = os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages")
        if os.path.exists(winget_base):
            # Ищем все папки с FFmpeg
            for item in os.listdir(winget_base):
                if "ffmpeg" in item.lower():
                    ffmpeg_dir = os.path.join(winget_base, item)
                    # Ищем в подпапках
                    for root, dirs, files in os.walk(ffmpeg_dir):
                        if "ffmpeg.exe" in files:
                            candidate_ffmpeg = os.path.join(root, "ffmpeg.exe")
                            candidate_ffprobe = os.path.join(root, "ffprobe.exe")
                            if os.path.exists(candidate_ffmpeg):
                                ffmpeg_path = candidate_ffmpeg
                                if os.path.exists(candidate_ffprobe):
                                    ffprobe_path = candidate_ffprobe
                                logger.info(f"ffmpeg найден через winget: {ffmpeg_path}")
                                break
                    if ffmpeg_path:
                        break
        
        # Если не нашли через winget, проверяем стандартные пути
        if not ffmpeg_path:
            for base_path in possible_paths:
                if "*" in base_path:
                    matches = glob.glob(base_path)
                    for match in matches:
                        candidate_ffmpeg = os.path.join(match, "ffmpeg.exe")
                        candidate_ffprobe = os.path.join(match, "ffprobe.exe")
                        if os.path.exists(candidate_ffmpeg):
                            ffmpeg_path = candidate_ffmpeg
                            if os.path.exists(candidate_ffprobe):
                                ffprobe_path = candidate_ffprobe
                            logger.info(f"ffmpeg найден: {ffmpeg_path}")
                            break
                elif os.path.exists(base_path):
                    candidate_ffmpeg = os.path.join(base_path, "ffmpeg.exe")
                    candidate_ffprobe = os.path.join(base_path, "ffprobe.exe")
                    if os.path.exists(candidate_ffmpeg):
                        ffmpeg_path = candidate_ffmpeg
                        if os.path.exists(candidate_ffprobe):
                            ffprobe_path = candidate_ffprobe
                        logger.info(f"ffmpeg найден: {ffmpeg_path}")
                        break
                if ffmpeg_path:
                    break
    
    # Устанавливаем пути для pydub
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
        AudioSegment.ffmpeg = ffmpeg_path
        if ffprobe_path:
            AudioSegment.ffprobe = ffprobe_path
        else:
            # Пробуем найти ffprobe рядом с ffmpeg
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            ffprobe_candidate = os.path.join(ffmpeg_dir, "ffprobe.exe")
            if os.path.exists(ffprobe_candidate):
                AudioSegment.ffprobe = ffprobe_candidate
                logger.info(f"ffprobe найден рядом с ffmpeg: {ffprobe_candidate}")
            else:
                logger.warning(f"ffprobe не найден рядом с ffmpeg в {ffmpeg_dir}")
    else:
        logger.warning("ffmpeg не найден, оптимизация аудио будет отключена")
    
    _AUDIO_SEGMENT = AudioSegment
    PYDUB_AVAILABLE = True
    
    # Проверяем, доступен ли ffmpeg (пробуем простую операцию)
    try:
        # Пробуем создать пустой AudioSegment для проверки доступности ffmpeg
        test_segment = AudioSegment.silent(duration=100)
        del test_segment
        if ffmpeg_path:
            logger.info("ffmpeg доступен и работает")
    except Exception as ffmpeg_error:
        PYDUB_AVAILABLE = False
        _PYDUB_ERROR = f"ffmpeg недоступен: {ffmpeg_error}"
        logger.warning(f"ffmpeg найден, но не работает: {ffmpeg_error}")
        
except ImportError as e:
    PYDUB_AVAILABLE = False
    _PYDUB_ERROR = f"pydub не установлен: {e}"
except Exception as e:
    PYDUB_AVAILABLE = False
    _PYDUB_ERROR = f"Ошибка импорта pydub: {e}"

# Получаем конфигурацию из settings
CLOUDRU_IAM_KEY = settings.cloudru_iam_key
CLOUDRU_IAM_SECRET = settings.cloudru_iam_secret
MODEL_URL = settings.whisper_model_url
MODEL_NAME = settings.whisper_model_name
IAM_TOKEN_URL = settings.cloud_iam_token_url

# Проверяем наличие обязательных переменных для работы с API
if not all([CLOUDRU_IAM_KEY, CLOUDRU_IAM_SECRET, MODEL_URL]):
    logger.warning("Не все переменные окружения для Cloud.ru API установлены. Проверьте .env файл")
    logger.warning(f"CLOUDRU_IAM_KEY: {'установлен' if CLOUDRU_IAM_KEY else 'НЕ установлен'}")
    logger.warning(f"CLOUDRU_IAM_SECRET: {'установлен' if CLOUDRU_IAM_SECRET else 'НЕ установлен'}")
    logger.warning(f"MODEL_URL: {MODEL_URL if MODEL_URL else 'НЕ установлен'}")


async def get_bearer_token() -> str:
    """
    Получает Bearer токен через OAuth2 client_credentials flow для Cloud.ru API.
    Согласно документации Cloud.ru, нужно сначала получить токен, затем использовать его.
    
    Returns:
        Bearer токен для авторизации запросов
    """
    try:
        # Параметры для OAuth2 client_credentials flow
        data = {
            'grant_type': 'client_credentials',
            'client_id': CLOUDRU_IAM_KEY,
            'client_secret': CLOUDRU_IAM_SECRET
        }
        
        response = requests.post(
            IAM_TOKEN_URL,
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


# Флаг для однократного логирования статуса pydub
_PYDUB_STATUS_LOGGED = False

def optimize_audio(audio_data: bytes, input_format: str = "ogg") -> bytes:
    """
    Оптимизирует аудио для Whisper API:
    - Конвертирует в 16 kHz sample rate (оптимально для Whisper)
    - Конвертирует в WAV формат
    - Делает моно (если stereo)
    
    Args:
        audio_data: Байты исходного аудио
        input_format: Формат исходного аудио (ogg, mp3, wav и т.д.)
    
    Returns:
        Оптимизированные байты аудио в формате WAV
    """
    global _PYDUB_STATUS_LOGGED
    
    if not PYDUB_AVAILABLE or _AUDIO_SEGMENT is None:
        # Если pydub не доступен, возвращаем исходные данные
        if not _PYDUB_STATUS_LOGGED:
            error_msg = _PYDUB_ERROR or "неизвестная причина"
            logger.warning(f"pydub недоступен ({error_msg}), используем исходное аудио без оптимизации")
            _PYDUB_STATUS_LOGGED = True
        return audio_data
    
    # Логируем статус только один раз
    if not _PYDUB_STATUS_LOGGED:
        logger.info("pydub доступен, оптимизация аудио включена")
        _PYDUB_STATUS_LOGGED = True
    
    try:
        logger.info(f"Начинаем оптимизацию аудио (формат: {input_format})...")
        # Загружаем аудио из байтов
        audio = _AUDIO_SEGMENT.from_file(BytesIO(audio_data), format=input_format)
        logger.info(f"Аудио загружено: {audio.frame_rate} Hz, {audio.channels} канал(ов), длительность: {len(audio)}ms")
        
        # Оптимизируем:
        # 1. Конвертируем в моно (если stereo)
        original_channels = audio.channels
        if audio.channels > 1:
            audio = audio.set_channels(1)
            logger.info(f"Конвертировано в моно (было {original_channels} каналов)")
        
        # 2. Устанавливаем sample rate 16 kHz (оптимально для Whisper)
        original_rate = audio.frame_rate
        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)
            logger.info(f"Sample rate изменен: {original_rate} -> 16000 Hz")
        
        # 3. Нормализуем битрейт (16-bit для WAV)
        audio = audio.set_sample_width(2)  # 16-bit = 2 bytes
        logger.info("Битрейт установлен: 16-bit")
        
        # 4. Экспортируем в WAV формат
        logger.info("Экспортируем в WAV формат...")
        output = BytesIO()
        audio.export(output, format="wav")
        output.seek(0)
        optimized_data = output.read()
        
        logger.info(f"✓ Аудио оптимизировано: {len(audio_data)} -> {len(optimized_data)} байт "
                   f"(уменьшение: {((1 - len(optimized_data)/len(audio_data)) * 100):.1f}%), "
                   f"sample rate: {audio.frame_rate} Hz, channels: {audio.channels}")
        
        return optimized_data
        
    except Exception as e:
        error_msg = str(e).lower()
        if 'ffmpeg' in error_msg or 'ffprobe' in error_msg:
            logger.warning(f"ffmpeg не найден. Для оптимизации аудио установите ffmpeg. Используем исходные данные.")
        else:
            logger.warning(f"Не удалось оптимизировать аудио: {e}. Используем исходные данные.")
        return audio_data


async def transcribe_via_direct_http(audio_data: bytes, audio_format: str = "ogg") -> str:
    """
    Прямой HTTP запрос к Whisper API через endpoint.
    Использует OAuth2 Bearer токен для авторизации согласно документации Cloud.ru.
    
    Args:
        audio_data: Байты аудио файла
        audio_format: Формат исходного аудио (ogg, mp3, wav и т.д.)
        
    Returns:
        Транскрибированный текст
    """
    try:
        if not MODEL_URL:
            raise ValueError("MODEL_URL не установлен. Проверьте переменные окружения.")
        
        # Оптимизируем аудио перед отправкой (уменьшаем размер и ускоряем обработку)
        logger.info(f"Оптимизируем аудио (исходный размер: {len(audio_data)} байт)...")
        optimized_audio = optimize_audio(audio_data, input_format=audio_format)
        
        # Согласно документации OpenAI, Whisper использует endpoint /v1/audio/transcriptions
        transcription_url = f"{MODEL_URL.rstrip('/')}/v1/audio/transcriptions"
        
        # Определяем формат и MIME type для оптимизированного аудио
        if PYDUB_AVAILABLE and optimized_audio != audio_data:
            # Если аудио было оптимизировано, оно в формате WAV
            file_name = 'audio.wav'
            mime_type = 'audio/wav'
        else:
            # Используем исходный формат
            file_name = f'audio.{audio_format}'
            mime_type = f'audio/{audio_format}'
        
        # Подготовка данных для multipart/form-data
        files = {
            'file': (file_name, optimized_audio, mime_type)
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
        logger.info("Внимание: Whisper может долго обрабатывать аудио (до 5-10 минут), это нормально")
        
        # Пробуем несколько раз с ретраями (serverless модель может долго стартовать после 5 минут простоя)
        # Для serverless моделей увеличиваем количество попыток, так как машина может отключаться
        max_retries = 5  # Увеличено до 5 попыток (всего 6) для serverless режима
        retry_delay = 10  # Задержка между попытками (секунды)
        timeout_retry_delay = 20  # Большая задержка после таймаута (модель может стартовать)
        timeout = 600  # 10 минут - покрываем общее время обработки (Whisper + Qwen)
        
        response = None
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # После таймаута делаем большую задержку, так как модель может стартовать
                    delay = timeout_retry_delay if isinstance(last_exception, requests.exceptions.Timeout) else retry_delay
                    logger.info(f"Повторная попытка {attempt}/{max_retries} через {delay} секунд...")
                    time.sleep(delay)
                
                response = requests.post(
                    transcription_url,
                    files=files,
                    data=data,
                    headers=auth_headers,
                    timeout=timeout
                )
                break  # Успешно, выходим из цикла
                
            except requests.exceptions.Timeout:
                last_exception = requests.exceptions.Timeout()
                if attempt < max_retries:
                    logger.warning(f"Таймаут при запросе к Whisper API (попытка {attempt + 1}/{max_retries + 1}). "
                                 f"Serverless модель может стартовать после простоя. Повторяем через {timeout_retry_delay} секунд...")
                    continue
                else:
                    logger.error(f"Таймаут при запросе к Whisper API после {max_retries + 1} попыток. "
                               f"Модель не отвечает за {timeout}s.")
                    raise
            except Exception as e:
                last_exception = e
                logger.error(f"Ошибка при запросе к Whisper API: {e}")
                if attempt < max_retries:
                    logger.info(f"Повторяем попытку через {retry_delay} секунд...")
                    continue
                else:
                    raise
        
        logger.info(f"Получен ответ со статусом {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                logger.info(f"Ответ от Whisper API (JSON): {result}")
                
                # Проверяем разные возможные форматы ответа
                text = result.get('text', '')
                if not text:
                    # Может быть другой формат
                    text = result.get('transcription', '')
                if not text:
                    # Может быть вложенная структура
                    if isinstance(result, dict):
                        for key in ['result', 'data', 'content']:
                            if key in result:
                                nested = result[key]
                                if isinstance(nested, dict):
                                    text = nested.get('text', '') or nested.get('transcription', '')
                                elif isinstance(nested, str):
                                    text = nested
                                if text:
                                    break
                
                logger.info(f"Извлеченный текст из ответа: '{text}' (длина: {len(text)})")
                
                if text:
                    logger.info("Успешно получена транскрипция")
                    return text
                else:
                    logger.warning(f"API вернул пустой текст в ответе. Полный ответ: {result}")
                    return ""
            except Exception as e:
                logger.error(f"Ошибка при парсинге JSON ответа: {e}")
                logger.error(f"Сырой ответ (первые 500 символов): {response.text[:500]}")
                raise
        elif response.status_code == 504 or response.status_code == 408:
            logger.error(f"Таймаут на стороне сервера (статус {response.status_code})")
            raise TimeoutError("Сервер обрабатывает запрос слишком долго. Попробуйте позже.")
        else:
            # Логируем детали ошибки для отладки
            try:
                error_detail = response.json()
                logger.error(f"Ошибка API (status {response.status_code}): {error_detail}")
            except:
                logger.error(f"Ошибка API (status {response.status_code}): {response.text}")
            raise ValueError(f"Ошибка API: статус {response.status_code}")

            
    except requests.exceptions.Timeout as e:
        # Это должно быть обработано внутри цикла ретраев, но на всякий случай оставляем
        logger.error(f"Таймаут при запросе к Whisper API (после всех ретраев): {e}")
        raise TimeoutError("Превышено время ожидания ответа от сервера транскрипции. Попробуйте позже или отправьте более короткое сообщение.")
    except Exception as e:
        logger.error(f"Ошибка при прямом HTTP запросе: {e}", exc_info=True)
        raise



async def transcribe_audio(audio_file: BytesIO, audio_format: str = "ogg") -> str:
    """
    Отправляет аудио файл на Whisper API для транскрипции.
    
    Args:
        audio_file: BytesIO объект с аудио данными
        audio_format: Формат аудио (ogg, mp3, wav и т.д.)
        
    Returns:
        Транскрибированный текст
    """
    try:
        audio_file.seek(0)
        audio_data = audio_file.read()
        
        # Используем прямой HTTP запрос к правильному endpoint
        return await transcribe_via_direct_http(audio_data, audio_format=audio_format)
            
    except Exception as e:
        logger.error(f"Ошибка при транскрипции: {e}", exc_info=True)
        raise

