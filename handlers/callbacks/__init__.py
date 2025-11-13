from aiogram import Router

from .feedback import router as feedback_router
from .menu import router as menu_router
from .profile import router as profile_router
from .quiz import router as quiz_router
from .touch_questions import router as touch_questions_router

router = Router()
router.include_router(menu_router)
router.include_router(feedback_router)
router.include_router(quiz_router)
router.include_router(profile_router)
router.include_router(touch_questions_router)

__all__ = ["router"]


