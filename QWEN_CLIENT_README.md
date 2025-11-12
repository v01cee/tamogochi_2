# Qwen Client для Cloud.ru API

Клиент для работы с Qwen API на платформе Cloud.ru. Предоставляет простой интерфейс для генерации ответов через модель Qwen, развернутую на Cloud.ru.

## Описание

`qwen_client.py` - это независимый модуль для генерации ответов через Qwen API на Cloud.ru. Модуль автоматически обрабатывает:
- OAuth2 авторизацию через Cloud.ru IAM
- Получение и кэширование Bearer токенов
- Отправку запросов к API
- Обработку ошибок
- Настройку параметров генерации

## Требования

### Python версия
- Python 3.8 или выше

## Настройка

### Переменные окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```env
# Cloud.ru IAM credentials (обязательно)
CLOUDRU_IAM_KEY=your_key_id_here
CLOUDRU_IAM_SECRET=your_secret_id_here

# URL модели Qwen на Cloud.ru (обязательно)
CLOUD_PUBLIC_URL=https://your-qwen-model-id.modelrun.inference.cloud.ru

# Имя модели Qwen (опционально, по умолчанию: model-run-sp9jm-police)
QWEN_MODEL=model-run-sp9jm-police

# Системный промпт (опционально)
SYSTEM_PROMPT=Ты - полезный ассистент. Отвечай на русском языке.

# Параметры генерации (опционально)
QWEN_MAX_TOKENS=768
QWEN_TEMPERATURE=0.2
QWEN_TOP_P=0.9
QWEN_TOP_K=10
QWEN_FREQUENCY_PENALTY=0.0
QWEN_REPETITION_PENALTY=1.03
QWEN_LENGTH_PENALTY=1.0
QWEN_STOP=["User:", "System:"]
CLOUD_TIMEOUT=180
```


## Использование

### Базовый пример

```python
from qwen_client import generate_qwen_response

# Простой запрос
try:
    response = await generate_qwen_response("Привет! Как дела?")
    print(f"Ответ: {response}")
except Exception as e:
    print(f"Ошибка: {e}")
```

### Пример с использованием класса напрямую

```python
from qwen_client import get_qwen_client

# Получаем клиент
client = get_qwen_client()

# Генерируем ответ
response = client.generate_response("Расскажи о Python")
print(response)
```

### Пример с историей диалога

```python
from qwen_client import get_qwen_client

client = get_qwen_client()

# История диалога
conversation = [
    {"role": "user", "content": "Меня зовут Иван"},
    {"role": "assistant", "content": "Приятно познакомиться, Иван!"}
]

# Новое сообщение с учетом истории
response = client.generate_response(
    "Как меня зовут?",
    conversation_history=conversation
)
print(response)  # Ответит: "Вас зовут Иван"
```


## Настройка параметров генерации

Все параметры генерации настраиваются через переменные окружения:

- **`QWEN_MAX_TOKENS`** (по умолчанию: 768) - Максимальное количество токенов в ответе
- **`QWEN_TEMPERATURE`** (по умолчанию: 0.2) - Температура сэмплинга (0.0-2.0)
- **`QWEN_TOP_P`** (по умолчанию: 0.9) - Nucleus sampling (0.0-1.0)
- **`QWEN_TOP_K`** (по умолчанию: 10) - Top-K sampling
- **`QWEN_FREQUENCY_PENALTY`** (по умолчанию: 0.0) - Штраф за частоту токенов
- **`QWEN_REPETITION_PENALTY`** (по умолчанию: 1.03) - Штраф за повторения
- **`QWEN_LENGTH_PENALTY`** (по умолчанию: 1.0) - Штраф за длину
- **`QWEN_STOP`** (по умолчанию: `["User:", "System:"]`) - Стоп-слова (JSON массив)
- **`CLOUD_TIMEOUT`** (по умолчанию: 180) - Таймаут запросов в секундах

## Системный промпт

Системный промпт настраивается через переменную окружения `SYSTEM_PROMPT`:

```env
SYSTEM_PROMPT=Ты - полезный ассистент. Отвечай на русском языке кратко и по делу.
```

Если переменная не установлена, используется промпт по умолчанию: `"Ты - полезный ассистент. Отвечай на русском языке."`
