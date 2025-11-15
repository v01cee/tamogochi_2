from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards import KeyboardOperations
from core.states import ProfileStates
from core.texts import get_booking_text
from database.session import get_session
from repositories.user_repository import UserRepository

from .summary import _send_main_menu

router = Router()
keyboard_ops = KeyboardOperations()


@router.callback_query(F.data == "edit_profile_personal_data")
async def callback_edit_profile_personal_data(callback: CallbackQuery, state: FSMContext):
    """Выбор редактируемого поля персональных данных."""
    edit_text = get_booking_text("edit_field_question")
    edit_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "ФИО": "edit_name",
            "Компания": "edit_company",
            "Должность": "edit_role",
        },
        interval=1,
    )
    await callback.message.answer(edit_text, reply_markup=edit_keyboard)
    await callback.answer()


@router.callback_query(F.data == "edit_name")
async def callback_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование ФИО."""
    name_text = get_booking_text("edit_name_request")
    await callback.message.answer(name_text)
    await state.set_state(ProfileStates.editing_name)
    await callback.answer()


@router.callback_query(F.data == "edit_role")
async def callback_edit_role(callback: CallbackQuery, state: FSMContext):
    """Редактирование должности."""
    role_text = get_booking_text("edit_role_request")
    await callback.message.answer(role_text)
    await state.set_state(ProfileStates.editing_role)
    await callback.answer()


@router.callback_query(F.data == "edit_company")
async def callback_edit_company(callback: CallbackQuery, state: FSMContext):
    """Редактирование компании."""
    company_text = get_booking_text("edit_company_request")
    await callback.message.answer(company_text)
    await state.set_state(ProfileStates.editing_company)
    await callback.answer()


@router.callback_query(F.data == "confirm_profile_personal_data")
async def callback_confirm_profile_personal_data(callback: CallbackQuery, state: FSMContext):
    """Переход к информации о старте курса после подтверждения данных."""
    data = await state.get_data()
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_or_create(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            language_code=callback.from_user.language_code,
        )
        update_payload = {}
        for field in ("full_name", "role", "company", "username"):
            value = data.get(field)
            if value:
                update_payload[field] = value
        # Устанавливаем is_first_visit = False, так как пользователь завершил онбординг
        update_payload["is_first_visit"] = False
        user_repo.update(user.id, **update_payload)
    finally:
        session.close()

    start_info_text = get_booking_text("course_start_info")
    start_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "ЧАТ ЕДИНОМЫШЛЕННИКОВ": "community_chat",
            "Настроить уведомления от бота": "setup_notifications",
        },
        interval=1,
    )
    await callback.message.answer(start_info_text, reply_markup=start_keyboard)
    await callback.answer()


@router.callback_query(F.data == "community_chat")
async def callback_community_chat(callback: CallbackQuery):
    """Заглушка перехода в чат."""
    await callback.answer("Чат будет добавлен позже")


@router.callback_query(F.data == "setup_notifications")
async def callback_setup_notifications(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню после настройки уведомлений."""
    await _send_main_menu(callback, state)
    await callback.answer()



