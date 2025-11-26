# ⚡ Быстрый старт на сервере

## Минимальные шаги для запуска

1. **Создайте .env файл:**
```bash
cp env.example .env
# Отредактируйте .env и заполните все переменные
```

2. **Запустите деплой:**
```bash
# Linux/macOS
chmod +x deploy.sh && ./deploy.sh

# Windows
.\deploy.ps1
```

3. **Проверьте работу:**
```bash
docker-compose ps
docker-compose logs -f bot
```

## Обязательные переменные в .env

Минимум для запуска:

```env
BOT_TOKEN=ваш_токен_бота
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=пароль
POSTGRES_DB=название_бд
SECRET_KEY=случайная_строка
```

Остальные переменные можно заполнить позже.

## Проверка после запуска

- Бот должен отвечать на `/start` в Telegram
- Админка доступна на `http://сервер:8042/admin/`
- Логи без ошибок: `docker-compose logs bot`

## Если что-то не работает

1. Проверьте логи: `docker-compose logs bot`
2. Проверьте .env файл
3. Убедитесь что PostgreSQL и Redis доступны
4. См. полную инструкцию в [DEPLOY.md](DEPLOY.md)

