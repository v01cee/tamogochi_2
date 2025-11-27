#!/bin/bash
# Скрипт для исправления проблемы с миграциями на сервере

echo "🔍 Проверка текущего состояния..."

# Проверяем что в базе
VERSION_IN_DB=$(docker-compose exec -T bot python -c "
from database.session import get_session
from sqlalchemy import text
session = next(get_session())
result = session.execute(text('SELECT * FROM alembic_version'))
row = result.fetchone()
if row:
    print(row[0])
else:
    print('EMPTY')
session.close()
" 2>/dev/null | tr -d '\n\r ')

echo "Версия в БД: $VERSION_IN_DB"

# Проверяем текущую версию через alembic
echo ""
echo "Текущая версия через alembic:"
docker-compose exec bot alembic current 2>&1 | head -5

echo ""
echo "Попытка применить миграции до head..."
docker-compose exec bot alembic upgrade head

echo ""
echo "Проверка после применения:"
docker-compose exec bot alembic current

