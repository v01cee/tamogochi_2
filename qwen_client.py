"""
Клиент для работы с Qwen API на Cloud.ru.
Обрабатывает авторизацию и генерацию ответов через модель Qwen.
"""
import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Получаем конфигурацию из переменных окружения
CLOUDRU_IAM_KEY = os.getenv('CLOUDRU_IAM_KEY')
CLOUDRU_IAM_SECRET = os.getenv('CLOUDRU_IAM_SECRET')
CLOUD_PUBLIC_URL = os.getenv('CLOUD_PUBLIC_URL')  # URL модели Qwen
QWEN_MODEL = os.getenv('QWEN_MODEL', 'library/qwen3-vl:32b')
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT', 'Ты - полезный ассистент. Отвечай на русском языке.')

# Параметры генерации
QWEN_MAX_TOKENS = int(os.getenv('QWEN_MAX_TOKENS', '768'))
QWEN_TEMPERATURE = float(os.getenv('QWEN_TEMPERATURE', '0.2'))
QWEN_TOP_P = float(os.getenv('QWEN_TOP_P', '0.9'))
QWEN_TOP_K = int(os.getenv('QWEN_TOP_K', '10'))
QWEN_FREQUENCY_PENALTY = float(os.getenv('QWEN_FREQUENCY_PENALTY', '0.0'))
QWEN_REPETITION_PENALTY = float(os.getenv('QWEN_REPETITION_PENALTY', '1.03'))
QWEN_LENGTH_PENALTY = float(os.getenv('QWEN_LENGTH_PENALTY', '1.0'))
QWEN_STOP = json.loads(os.getenv('QWEN_STOP', '["User:", "System:"]'))
CLOUD_TIMEOUT = int(os.getenv('CLOUD_TIMEOUT', '180'))

# IAM endpoint
IAM_TOKEN_URL = os.getenv(
    'CLOUD_IAM_TOKEN_URL',
    'https://auth.iam.sbercloud.ru/auth/system/openid/token'
)

# Проверяем наличие обязательных переменных
if not all([CLOUDRU_IAM_KEY, CLOUDRU_IAM_SECRET, CLOUD_PUBLIC_URL]):
    logger.warning("Не все переменные окружения для Cloud.ru Qwen API установлены. Проверьте .env файл")


class QwenClient:
    """
    Клиент для работы с моделью Qwen на Cloud.ru.
    Обрабатывает авторизацию через OAuth2 и генерацию ответов.
    """
    
    def __init__(self):
        self.base_url = CLOUD_PUBLIC_URL
        self.key_id = CLOUDRU_IAM_KEY
        self.key_secret = CLOUDRU_IAM_SECRET
        self.model_name = QWEN_MODEL
        self.timeout = CLOUD_TIMEOUT
        self.system_prompt = SYSTEM_PROMPT
        
        # Параметры генерации
        self.max_tokens = QWEN_MAX_TOKENS
        self.temperature = QWEN_TEMPERATURE
        self.top_p = QWEN_TOP_P
        self.top_k = QWEN_TOP_K
        self.frequency_penalty = QWEN_FREQUENCY_PENALTY
        self.repetition_penalty = QWEN_REPETITION_PENALTY
        self.length_penalty = QWEN_LENGTH_PENALTY
        self.stop = QWEN_STOP
        self.iam_token_url = IAM_TOKEN_URL
        
        # Кэш токена
        self._access_token: Optional[str] = None
        self._token_expire_at: float = 0.0
        
        if not self.base_url or not self.key_id or not self.key_secret:
            raise RuntimeError("Нужны CLOUD_PUBLIC_URL, CLOUDRU_IAM_KEY и CLOUDRU_IAM_SECRET")
    
    def _have_valid_token(self) -> bool:
        """Проверяет, есть ли валидный токен (с запасом 30 секунд)."""
        return bool(self._access_token) and (time.time() < self._token_expire_at - 30)
    
    def _fetch_token(self) -> None:
        """Получает новый Bearer токен через OAuth2."""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.key_id,
            "client_secret": self.key_secret,
        }
        
        resp = requests.post(self.iam_token_url, data=data, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"IAM token error HTTP {resp.status_code}: {resp.text[:400]}")
        
        try:
            payload = resp.json()
        except Exception:
            raise RuntimeError(f"IAM вернул не-JSON: {resp.text[:400]}")
        
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 3600))
        if not access_token:
            raise RuntimeError(f"IAM: нет access_token в ответе: {payload}")
        
        self._access_token = access_token
        self._token_expire_at = time.time() + max(60, expires_in)
        logger.info("Успешно получен Bearer токен для Qwen")
    
    def _auth_headers(self) -> Dict[str, str]:
        """Получает заголовки авторизации с Bearer токеном."""
        if not self._have_valid_token():
            self._fetch_token()
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    
    def generate_response(self, user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Генерирует ответ на сообщение пользователя.
        
        Args:
            user_message: Сообщение пользователя
            conversation_history: История диалога (опционально)
        
        Returns:
            Ответ модели
        """
        # Формируем сообщения для API
        messages = []
        
        # Добавляем системный промпт
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        # Добавляем историю диалога, если есть
        if conversation_history:
            messages.extend(conversation_history)
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос
        url = self.base_url.rstrip("/") + "/v1/chat/completions"
        body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "frequency_penalty": self.frequency_penalty,
            "repetition_penalty": self.repetition_penalty,
            "length_penalty": self.length_penalty,
            "max_tokens": self.max_tokens,
            "stop": self.stop,
            "stream": False,
        }
        
        t0 = time.time()
        resp = requests.post(
            url,
            headers=self._auth_headers(),
            json=body,
            timeout=self.timeout
        )
        llm_ms = round((time.time() - t0) * 1000, 2)
        
        # Авторизационный 401 — пробуем обновить токен 1 раз
        if resp.status_code == 401:
            logger.warning("Получен 401, обновляем токен")
            self._fetch_token()
            resp = requests.post(
                url,
                headers=self._auth_headers(),
                json=body,
                timeout=self.timeout
            )
        
        if resp.status_code >= 400:
            txt = (resp.text or "")[:600]
            logger.error(f"Cloud.ru error HTTP {resp.status_code}: {txt}")
            raise RuntimeError(f"Cloud.ru error HTTP {resp.status_code}: {txt}")
        
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"Cloud.ru вернул не-JSON: {resp.text[:400]}")
        
        # Извлекаем ответ
        choices = data.get("choices") or []
        content = ""
        if choices:
            msg = choices[0].get("message") or {}
            content = (msg.get("content") or "").strip()
            if not content:
                content = (choices[0].get("text") or "").strip()
        
        if not content:
            logger.warning("Пустой ответ от модели")
            content = "Извините, не удалось получить ответ от модели."
        
        logger.info(f"Получен ответ от Qwen (время: {llm_ms}ms)")
        return content
    
    def health_check(self) -> Dict[str, Any]:
        """
        Проверяет работоспособность API.
        
        Returns:
            Словарь со статусом проверки
        """
        try:
            test_response = self.generate_response("Привет")
            return {
                "status": "ok",
                "model": self.model_name,
                "api_type": "cloudru-chat-completions",
                "response_length": len(test_response)
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# Глобальный экземпляр клиента (singleton)
_qwen_client: Optional[QwenClient] = None


def get_qwen_client() -> QwenClient:
    """
    Получает глобальный экземпляр клиента Qwen (singleton).
    
    Returns:
        Экземпляр QwenClient
    """
    global _qwen_client
    if _qwen_client is None:
        _qwen_client = QwenClient()
    return _qwen_client


async def generate_qwen_response(user_message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Асинхронная обертка для генерации ответа Qwen.
    
    Args:
        user_message: Сообщение пользователя
        conversation_history: История диалога (опционально)
    
    Returns:
        Ответ модели
    """
    client = get_qwen_client()
    # Выполняем синхронный запрос в отдельном потоке (для async совместимости)
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, client.generate_response, user_message, conversation_history)

