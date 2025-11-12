from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from core.keyboards import KeyboardOperations
from core.states import ProfileStates
from core.texts import get_booking_text
from database.session import get_session
from repositories.user_repository import UserRepository

router = Router()
keyboard_ops = KeyboardOperations()


@router.callback_query(F.data == "free_week")
async def callback_free_week(callback: CallbackQuery, state: FSMContext):
    """Выбор бесплатной недели."""
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
        user_repo.update(
            user.id,
            subscription_type="free_week",
            subscription_started_at=datetime.now(timezone.utc),
        )
    finally:
        session.close()

    ready_text = get_booking_text("free_week_ready")
    await callback.message.answer(ready_text)

    consent_text = get_booking_text("personal_data_consent")
    consent_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Далее": "consent_agree",
            "Не согласен": "consent_disagree",
        },
        interval=2,
    )
    await callback.message.answer(consent_text, reply_markup=consent_keyboard)
    await callback.answer()


@router.callback_query(F.data == "consent_agree")
async def callback_consent_agree(callback: CallbackQuery, state: FSMContext):
    """Согласие на обработку и запрос имени."""
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
        user_repo.update(
            user.id,
            consent_accepted_at=datetime.now(timezone.utc),
        )
    finally:
        session.close()

    name_text = get_booking_text("name_request")
    await callback.message.answer(name_text)
    await state.set_state(ProfileStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "username_confirm_yes")
async def callback_username_confirm_yes(callback: CallbackQuery, state: FSMContext):
    """Подтверждение ника и выбор роли."""
    role_text = get_booking_text("role_request")
    role_keyboard = await keyboard_ops.create_keyboard(
        buttons={
            "Собственник бизнеса": "role_business_owner",
            "СЕО": "role_ceo",
            "Топ-менеджер": "role_top_manager",
            "Middle-руководитель": "role_middle_manager",
            "Специалист": "role_specialist",
            "Другое": "role_other",
        },
        interval=2,
    )
    await callback.message.answer(role_text, reply_markup=role_keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("role_"))
async def callback_role_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор роли пользователя."""
    role_data = callback.data.replace("role_", "")

    if role_data == "other":
        await callback.message.answer("Напишите вашу профессиональную роль/должность:")
        await state.set_state(ProfileStates.waiting_for_role)
    else:
        role_mapping = {
            "business_owner": "Собственник бизнеса",
            "ceo": "СЕО",
            "top_manager": "Топ-менеджер",
            "middle_manager": "Middle-руководитель",
            "specialist": "Специалист",
        }
        role = role_mapping.get(role_data, role_data)
        await state.update_data(role=role)

        company_text = get_booking_text("company_request")
        await callback.message.answer(company_text)
        await state.set_state(ProfileStates.waiting_for_company)

    await callback.answer()


@router.callback_query(F.data == "username_confirm_no")
async def callback_username_confirm_no(callback: CallbackQuery, state: FSMContext):
    """Отказ от подтверждения ника и повторный запрос."""
    username_text = get_booking_text("username_request")
    await callback.message.answer(username_text)
    await state.set_state(ProfileStates.waiting_for_username)
    await callback.answer()


@router.callback_query(F.data == "monthly_subscription")
async def callback_monthly_subscription(callback: CallbackQuery, state: FSMContext):
    """Заглушка платной подписки."""
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
        user_repo.update(
            user.id,
            subscription_type="monthly",
            subscription_paid_at=datetime.now(timezone.utc),
            subscription_started_at=datetime.now(timezone.utc),
        )
    finally:
        session.close()

    await callback.answer("Подписка на месяц будет добавлена позже")



