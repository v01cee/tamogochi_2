#!/bin/bash
# Скрипт для исправления и применения миграций

set -e

echo "🚀 Начинаем применение миграций..."

# Проверяем подключение к БД
echo "📡 Проверка подключения к базе данных..."
docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "SELECT 1;" > /dev/null || {
    echo "❌ Ошибка подключения к базе данных!"
    exit 1
}

# Проверяем, существует ли таблица alembic_version
echo "🔍 Проверка таблицы alembic_version..."
TABLE_EXISTS=$(docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version');" 2>/dev/null || echo "false")

if [ "$TABLE_EXISTS" = "f" ] || [ "$TABLE_EXISTS" = "false" ]; then
    echo "⚠️  Таблица alembic_version не существует. Создаём её..."
    docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num));" || {
        echo "❌ Не удалось создать таблицу alembic_version"
        exit 1
    }
    echo "✅ Таблица alembic_version создана"
fi

# Проверяем текущую версию
CURRENT_VERSION=$(docker-compose exec -T bot alembic current 2>&1 | grep -oP '^\s*\K[0-9a-f_]+' || echo "none")

if [ "$CURRENT_VERSION" = "none" ] || [ -z "$CURRENT_VERSION" ]; then
    echo "⚠️  Миграции не применены или база пустая"
    
    # Проверяем, есть ли уже таблицы
    TABLES_COUNT=$(docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT IN ('alembic_version', 'spatial_ref_sys');" 2>/dev/null || echo "0")
    
    if [ "$TABLES_COUNT" -gt "0" ]; then
        echo "⚠️  В базе уже есть таблицы. Проверьте состояние вручную!"
        echo "📋 Список таблиц:"
        docker-compose exec -T postgres psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-app_db} -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
        echo ""
        echo "💡 Если таблицы уже есть, но миграции не применены, используйте:"
        echo "   docker-compose exec bot alembic stamp head"
        echo "   или"
        echo "   docker-compose exec bot alembic stamp 0003_add_touch_answers_evening_reflections_ratings_saturday"
    else
        echo "✅ База данных пустая. Применяем миграции с нуля..."
        docker-compose exec bot alembic upgrade head
    fi
else
    echo "📌 Текущая версия: $CURRENT_VERSION"
    echo "🔄 Применяем миграции до head..."
    docker-compose exec bot alembic upgrade head
fi

echo ""
echo "✅ Проверка итогового состояния:"
docker-compose exec bot alembic current

echo ""
echo "🎉 Миграции применены!"

