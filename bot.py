import asyncio
import logging
import limited_aiogram
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from core.config import settings
from handlers.start import router as start_router
from handlers.callbacks import router as callbacks_router
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения")
    
    # Используем LimitedBot для автоматического контроля лимитов Telegram API
    bot = limited_aiogram.LimitedBot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Сброс webhook перед запуском polling (если был установлен)
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            logger.info(f"Обнаружен активный webhook: {webhook_info.url}. Удаляем...")
            await bot.delete_webhook(drop_pending_updates=True)
            # Небольшая пауза, чтобы Telegram успел обработать запрос
            await asyncio.sleep(1)
            logger.info("Webhook успешно удален")
        else:
            logger.info("Webhook не установлен, продолжаем с polling")
    except Exception as e:
        logger.warning(f"Ошибка при проверке/удалении webhook: {e}. Продолжаем запуск...")

    # Инициализация FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(callbacks_router)

    scheduler = setup_scheduler(bot)

    logger.info("Бот запущен. Нажми Ctrl+C для остановки.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        raise
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


