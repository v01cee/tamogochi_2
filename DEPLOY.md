# 🚀 Инструкция по деплою на сервер

## Подготовка к деплою

### 1. Подготовка файла .env

Скопируйте `env.example` в `.env` и заполните все переменные:

```bash
cp env.example .env
```

**Обязательно заполните следующие переменные:**

- `BOT_TOKEN` - токен вашего Telegram бота (получить у @BotFather)
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` - настройки PostgreSQL
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` (если требуется) - настройки Redis
- `SECRET_KEY` - секретный ключ Django (сгенерируйте случайную строку)
- `ROBOKASSA_SHOP_ID`, `ROBOKASSA_PASSWORD1`, `ROBOKASSA_PASSWORD2` - настройки Robokassa
- `CLOUDRU_IAM_KEY`, `CLOUDRU_IAM_SECRET` - ключи Cloud.ru API
- `WHISPER_MODEL_URL`, `CLOUD_PUBLIC_URL` - URLs моделей Cloud.ru
- `AWS_S3_ENDPOINT_URL`, `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - настройки AWS S3 (если используется)

### 2. Генерация SECRET_KEY для Django

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Или онлайн: https://djecrety.ir/

### 3. Проверка зависимостей

Убедитесь, что на сервере установлены:
- Docker
- Docker Compose

Проверка:
```bash
docker --version
docker-compose --version
```

**Или используйте Docker Compose V2:**
```bash
docker compose version
```
*(Без дефиса - новая версия)*

## Настройка для внешних БД

Если вы используете внешние PostgreSQL и Redis (не из docker-compose):

1. **Закомментируйте сервисы postgres и redis** в `docker-compose.yml`:
```yaml
# postgres:
#   image: postgres:16
#   ...
#
# redis:
#   image: redis:7-alpine
#   ...
```

2. **Убедитесь, что в `.env` указаны правильные хосты** внешних БД:
```env
POSTGRES_HOST=ваш-внешний-host
POSTGRES_PORT=5432
REDIS_HOST=ваш-внешний-redis-host
REDIS_PORT=6379
```

3. **Удалите зависимости от postgres и redis** в сервисах bot и admin:
```yaml
bot:
  # depends_on:
  #   - postgres
  #   - redis
```

## Деплой

### Вариант 1: Автоматический деплой (рекомендуется)

**Для Linux/macOS:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Для Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**Примечание:** Если используете Docker Compose V2 (без дефиса), замените `docker-compose` на `docker compose` в скриптах или обновите их соответственно.

### Вариант 2: Ручной деплой

1. **Остановка старых контейнеров:**
```bash
docker-compose down
```

2. **Сборка образов:**
```bash
docker-compose build --no-cache
```

3. **Запуск контейнеров:**
```bash
docker-compose up -d
```

4. **Применение миграций Alembic:**
```bash
docker-compose exec bot alembic upgrade head
```

5. **Применение миграций Django:**
```bash
docker-compose exec admin python admin_panel/manage.py migrate --noinput
```

6. **Сборка статических файлов Django:**
```bash
docker-compose exec admin python admin_panel/manage.py collectstatic --noinput
```

7. **Создание суперпользователя Django (при первом запуске):**
```bash
docker-compose exec admin python admin_panel/manage.py createsuperuser
```

## Проверка работы

### Просмотр статуса контейнеров
```bash
docker-compose ps
```

### Просмотр логов

**Логи бота:**
```bash
docker-compose logs -f bot
```

**Логи админки:**
```bash
docker-compose logs -f admin
```

**Все логи:**
```bash
docker-compose logs -f
```

### Проверка работы бота

Откройте Telegram и отправьте команду `/start` вашему боту.

### Доступ к Django Admin

Откройте в браузере: `http://ваш-сервер:8042/admin/`

## Полезные команды

### Перезапуск сервисов
```bash
docker-compose restart bot      # Перезапуск бота
docker-compose restart admin    # Перезапуск админки
docker-compose restart          # Перезапуск всех сервисов
```

### Остановка
```bash
docker-compose down              # Остановка с удалением контейнеров
docker-compose stop              # Остановка без удаления
```

### Обновление кода

1. Получите последние изменения из git
2. Пересоберите и перезапустите:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
docker-compose exec bot alembic upgrade head
```

### Бэкап базы данных

```bash
docker-compose exec postgres pg_dump -U postgres app_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление базы данных

```bash
docker-compose exec -T postgres psql -U postgres app_db < backup.sql
```

## Устранение проблем

### Контейнер не запускается

1. Проверьте логи:
```bash
docker-compose logs bot
```

2. Проверьте .env файл:
```bash
cat .env
```

3. Проверьте доступность PostgreSQL и Redis:
```bash
docker-compose ps
```

### Бот не отвечает

1. Проверьте токен бота в .env
2. Проверьте логи бота:
```bash
docker-compose logs -f bot
```

### Ошибки миграций

#### Миграции не применены или зависли

**Проблема:** `alembic upgrade head` выполняется долго или не работает, миграции не применены.

**Решение:**

1. **Сначала проверьте состояние миграций:**
```bash
chmod +x check_migrations.sh
./check_migrations.sh
```

2. **Исправьте и примените миграции автоматически:**
```bash
chmod +x fix_migrations.sh
./fix_migrations.sh
```

3. **Или вручную (если скрипт не помог):**

   a. Проверьте подключение к БД:
   ```bash
   docker-compose exec bot alembic current
   ```

   b. Если таблица `alembic_version` не существует, создайте её:
   ```bash
   docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"
   ```

   c. Если база данных пустая (нет таблиц), примените миграции:
   ```bash
   docker-compose exec bot alembic upgrade head
   ```

   d. Если таблицы уже есть, но версия не записана, отметьте текущую версию:
   ```bash
   docker-compose exec bot alembic stamp head
   ```

4. **Проверьте подключение к БД:**
```bash
docker-compose exec bot python -c "from database.session import get_session; next(get_session())"
```

5. **Если миграции зависли, прервите и выполните вручную:**
```bash
# Остановите контейнер
docker-compose stop bot

# Примените миграции в отдельной сессии
docker-compose run --rm bot alembic upgrade head

# Запустите контейнер заново
docker-compose up -d bot
```

### Django Admin не открывается

1. Проверьте, что порт 8042 открыт в файрволе
2. Проверьте логи:
```bash
docker-compose logs admin
```

## Мониторинг

### Использование ресурсов
```bash
docker stats
```

### Состояние контейнеров
```bash
docker-compose ps
```

## Безопасность

⚠️ **ВАЖНО:**

1. **Никогда не коммитьте .env файл в git** - он уже добавлен в .gitignore
2. **Используйте сильные пароли** для PostgreSQL и Redis
3. **Генерируйте уникальный SECRET_KEY** для Django
4. **Ограничьте доступ к порту 8042** только для админов
5. **Регулярно делайте бэкапы** базы данных

## Дополнительная информация

- Полный список переменных окружения см. в `env.example`
- Архитектура проекта описана в `README.md`
- Для разработки локально используйте `docker-compose up`

