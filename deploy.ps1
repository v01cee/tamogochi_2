# Скрипт для деплоя на сервер (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Начинаем деплой..." -ForegroundColor Green

# Проверяем наличие .env файла
if (-not (Test-Path ".env")) {
    Write-Host "❌ Файл .env не найден!" -ForegroundColor Red
    Write-Host "Скопируйте env.example в .env и заполните все переменные:"
    Write-Host "Copy-Item env.example .env"
    exit 1
}

Write-Host "✅ Проверка .env файла пройдена" -ForegroundColor Green

# Останавливаем контейнеры если они запущены
Write-Host "🛑 Останавливаем старые контейнеры..." -ForegroundColor Yellow
docker-compose down 2>$null

# Собираем образы
Write-Host "🔨 Собираем Docker образы..." -ForegroundColor Yellow
docker-compose build --no-cache

# Запускаем контейнеры
Write-Host "▶️  Запускаем контейнеры..." -ForegroundColor Yellow
docker-compose up -d

# Ждем готовности PostgreSQL
Write-Host "⏳ Ждем готовности PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Применяем миграции Alembic
Write-Host "📦 Применяем миграции Alembic..." -ForegroundColor Yellow
docker-compose exec -T bot alembic upgrade head 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Миграции Alembic уже применены или БД недоступна" -ForegroundColor Yellow
}

# Применяем миграции Django
Write-Host "📦 Применяем миграции Django..." -ForegroundColor Yellow
docker-compose exec -T admin python admin_panel/manage.py migrate --noinput 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Миграции Django уже применены" -ForegroundColor Yellow
}

# Собираем статические файлы Django
Write-Host "📦 Собираем статические файлы Django..." -ForegroundColor Yellow
docker-compose exec -T admin python admin_panel/manage.py collectstatic --noinput 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Не удалось собрать статику" -ForegroundColor Yellow
}

# Проверяем статус контейнеров
Write-Host "📊 Статус контейнеров:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "✅ Деплой завершен!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Полезные команды:" -ForegroundColor Cyan
Write-Host "  Просмотр логов бота:        docker-compose logs -f bot"
Write-Host "  Просмотр логов админки:     docker-compose logs -f admin"
Write-Host "  Остановка:                  docker-compose down"
Write-Host "  Перезапуск:                 docker-compose restart"
Write-Host ""
Write-Host "🌐 Django Admin будет доступен на: http://localhost:8042/admin/" -ForegroundColor Cyan

