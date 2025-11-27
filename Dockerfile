FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Делаем скрипт ожидания исполняемым (если он уже скопирован)
# Если скрипт монтируется как volume, права нужно давать на хосте
RUN if [ -f wait-for-db.sh ]; then chmod +x wait-for-db.sh; fi

# Переменные окружения
ENV PYTHONUNBUFFERED=1

# Команда по умолчанию
CMD ["python", "bot.py"]


