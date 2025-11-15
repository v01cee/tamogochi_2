"""Helpers for Django admin configuration (split from admin.py)."""

# Import modules so that @admin.register decorators execute on import
from . import telegram_user_admin, quiz_and_course_admin, touch_content_admin  # noqa: F401

