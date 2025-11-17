import asyncio
import logging
from aiogram import Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from core.config import settings
from handlers.start import router as start_router
from handlers.callbacks import router as callbacks_router
from services.scheduler import setup_scheduler
from services.safe_bot import SafeBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    bot = SafeBot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Инициализация FSM storage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(start_router)
    dp.include_router(callbacks_router)

    scheduler = setup_scheduler(bot)

    logger.info("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")


if __name__ == "__main__":
    asyncio.run(main())


