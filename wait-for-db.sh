#!/bin/sh
# Скрипт ожидания готовности PostgreSQL

set -e

# Первый аргумент - host (из docker-compose передается имя сервиса)
host="$1"
shift
cmd="$@"

# Используем переменные окружения или дефолтные значения
user="${POSTGRES_USER:-postgres}"
port="${POSTGRES_PORT:-5432}"

# Если host не передан, используем дефолт
if [ -z "$host" ]; then
    host="${POSTGRES_HOST:-postgres}"
fi

until pg_isready -h "$host" -p "$port" -U "$user"; do
  >&2 echo "PostgreSQL недоступен - ожидание... (host=$host, port=$port, user=$user)"
  sleep 1
done

>&2 echo "PostgreSQL готов - выполняем команду"
exec sh -c "$cmd"

