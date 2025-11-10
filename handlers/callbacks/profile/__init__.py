from aiogram import Router

from .editing import router as editing_router
from .onboarding import router as onboarding_router
from .summary import router as summary_router

router = Router()
router.include_router(summary_router)
router.include_router(onboarding_router)
router.include_router(editing_router)

__all__ = ["router"]


