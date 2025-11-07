#!/bin/sh
# Скрипт ожидания готовности PostgreSQL

set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -U postgres; do
  >&2 echo "PostgreSQL недоступен - ожидание..."
  sleep 1
done

>&2 echo "PostgreSQL готов - выполняем команду"
exec $cmd

