# Whisper Client для Cloud.ru API

Клиент для работы с Whisper API на платформе Cloud.ru. Предоставляет простой интерфейс для транскрипции аудио файлов через модель Whisper, развернутую на Cloud.ru.

## Описание

`whisper_client.py` - это независимый модуль для транскрипции аудио через Whisper API на Cloud.ru. Модуль автоматически обрабатывает:
- OAuth2 авторизацию через Cloud.ru IAM
- Получение Bearer токенов
- Отправку запросов к API
- Обработку ошибок



### Переменные окружения

```env
# Cloud.ru IAM credentials (обязательно)
CLOUDRU_IAM_KEY=your_key_id_here
CLOUDRU_IAM_SECRET=your_secret_id_here

# URL модели на Cloud.ru (обязательно)
MODEL_URL=https://your-model-id.modelrun.inference.cloud.ru

# Имя модели (опционально, по умолчанию: model-run-wxryh-soft)
MODEL_NAME=model-run-wxryh-soft
```


### Базовый пример

```python
from io import BytesIO
from whisper_client import transcribe_audio

# Загрузите аудио файл в BytesIO
with open('audio.ogg', 'rb') as f:
    audio_data = BytesIO(f.read())

# Транскрибируйте аудио
try:
    text = await transcribe_audio(audio_data)
    print(f"Транскрипция: {text}")
except Exception as e:
    print(f"Ошибка: {e}")
```

## Поддерживаемые форматы аудио

Модуль поддерживает любые форматы аудио, которые поддерживает Whisper API:
- OGG (по умолчанию)
- MP3
- WAV
- M4A
- FLAC
- и другие форматы, поддерживаемые Whisper

## Настройка языка транскрипции

По умолчанию используется русский язык (`language: 'ru'`). Чтобы изменить язык, отредактируйте файл `whisper_client.py`:

Найдите строку:
```python
'language': 'ru',
```

И замените на нужный код языка (например, `'en'` для английского, `'auto'` для автоматического определения).

