import logging

from aiogram import Router
from aiogram.types import CallbackQuery

from .feedback import router as feedback_router
from .menu import router as menu_router
from .profile import router as profile_router
from .quiz import router as quiz_router
from .touch_questions import router as touch_questions_router
from .evening_rating import router as evening_rating_router

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query.middleware()
async def log_all_callback_queries(handler, event: CallbackQuery, data: dict):
    """Глобальный middleware для логирования всех callback queries"""
    logger.info(
        f"[CALLBACK] Пользователь {event.from_user.id} (@{event.from_user.username}) "
        f"нажал кнопку: {event.data}"
    )
    return await handler(event, data)


router.include_router(menu_router)
router.include_router(feedback_router)
router.include_router(quiz_router)
router.include_router(profile_router)
router.include_router(touch_questions_router)
router.include_router(evening_rating_router)

__all__ = ["router"]


