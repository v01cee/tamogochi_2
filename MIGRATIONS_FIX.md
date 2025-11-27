# 🔧 Решение проблем с миграциями

## Быстрое решение

Если миграции не применены на сервере:

### Ручное исправление

#### Шаг 1: Проверка состояния

```bash
# Проверьте текущую версию миграций
docker-compose exec bot alembic current

# Проверьте список доступных миграций
docker-compose exec bot alembic history
```

#### Шаг 2: Если таблица alembic_version не существует

```bash
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
"
```

#### Шаг 3: Применение миграций

**Если база данных пустая (нет таблиц users, touch_contents и т.д.):**

```bash
docker-compose exec bot alembic upgrade head
```

**Если таблицы уже есть, но версия не записана:**

```bash
# Отметьте последнюю применённую версию
docker-compose exec bot alembic stamp 0003_add_touch_answers_evening_reflections_ratings_saturday

# Или отметьте как head (если все миграции уже применены)
docker-compose exec bot alembic stamp head
```

#### Шаг 4: Проверка результата

```bash
# Проверьте текущую версию
docker-compose exec bot alembic current

# Должно показать: 0003_add_touch_answers_evening_reflections_ratings_saturday
```

## Диагностика проблем

### Команда зависла или выполняется долго

**Причина:** Возможно проблема с подключением к БД или блокировка таблиц.

**Решение:**

1. Прервите команду (Ctrl+C)

2. Проверьте подключение к БД:
```bash
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "SELECT 1;"
```

3. Проверьте логи бота:
```bash
docker-compose logs bot | tail -50
```

4. Если контейнер завис, перезапустите:
```bash
docker-compose restart bot
```

5. Примените миграции в отдельной сессии:
```bash
docker-compose run --rm bot alembic upgrade head
```

### Ошибка "Target database is not up to date"

**Решение:**
```bash
# Примените все миграции
docker-compose exec bot alembic upgrade head
```

### Ошибка "Can't locate revision identified by"

**Решение:**
Проверьте, что все файлы миграций на месте:
```bash
docker-compose exec bot ls -la migrations/versions/
```

Должны быть файлы:
- `0001_initial.py`
- `0002_add_day_evening_touch_sent_at.py`
- `0003_add_touch_answers_evening_reflections_ratings_saturday.py`

### База данных не пустая, но миграции не применены

**Решение:**

1. Проверьте, какие таблицы есть:
```bash
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
"
```

2. Если таблицы соответствуют миграции 0003, просто отметьте версию:
```bash
docker-compose exec bot alembic stamp head
```

3. Если таблицы частичные, определите какая миграция соответствует и отметьте её:
```bash
# Например, если есть только таблицы из 0001:
docker-compose exec bot alembic stamp 0001_initial

# Затем примените остальные:
docker-compose exec bot alembic upgrade head
```

## Полезные команды для диагностики

```bash
# Просмотр истории миграций
docker-compose exec bot alembic history --verbose

# Просмотр текущей версии с деталями
docker-compose exec bot alembic current --verbose

# Список всех таблиц в БД
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "\dt"

# Список всех колонок в таблице users
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "\d users"
```

## Структура миграций

Проект использует 3 миграции:

1. **0001_initial** - Создание базовых таблиц (users, course_days, touch_contents, quiz_results, payments)
2. **0002_add_day_evening_touch_sent_at** - Добавление полей day_touch_sent_at и evening_touch_sent_at в users
3. **0003_add_touch_answers_evening_reflections_ratings_saturday** - Создание таблиц для ответов, рефлексий и рейтингов

Последняя версия (head): `0003_add_touch_answers_evening_reflections_ratings_saturday`

