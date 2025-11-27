#!/bin/bash
# Скрипт для проверки состояния миграций на сервере

echo "🔍 Проверка подключения к базе данных..."
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "SELECT version();" || echo "❌ Нет доступа к базе данных"

echo ""
echo "🔍 Проверка существования таблицы alembic_version..."
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "SELECT * FROM alembic_version;" 2>/dev/null || echo "❌ Таблица alembic_version не существует"

echo ""
echo "🔍 Текущая версия миграций (если есть):"
docker-compose exec bot alembic current 2>&1 || echo "❌ Не удалось получить текущую версию"

echo ""
echo "🔍 Доступные миграции:"
docker-compose exec bot alembic history 2>&1 | head -20 || echo "❌ Не удалось получить историю миграций"

echo ""
echo "🔍 Проверка существования основных таблиц:"
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
" 2>/dev/null || echo "❌ Не удалось получить список таблиц"

