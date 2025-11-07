from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from core.texts import get_booking_text
from core.keyboards import KeyboardOperations
from core.states import FeedbackStates, QuizStates, ProfileStates
from database.session import get_session
from repositories.user_repository import UserRepository

router = Router()
keyboard_ops = KeyboardOperations()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик callback для помощи"""
    text = get_booking_text("help")
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "info")
async def callback_info(callback: CallbackQuery):
    """Обработчик callback для информации"""
    text = "Информация о боте"
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "course_start")
async def callback_course_start(callback: CallbackQuery):
    """Обработчик callback для начала курса"""
    text = get_booking_text("step_3")
    await callback.message.answer(text)
    
    # Отправляем шаг 4 после шага 3
    step_4_text = get_booking_text("step_4")
    await callback.message.answer(step_4_text)
    
    # Отправляем шаг 5 после шага 4 с кнопкой "Да, интересно!"
    step_5_text = get_booking_text("step_5")
    yes_buttons = {
        "Да, интересно!": "yes_interested"
    }
    yes_keyboard = await keyboard_ops.create_keyboard(buttons=yes_buttons, interval=1)
    await callback.message.answer(step_5_text, reply_markup=yes_keyboard)
    
    await callback.answer()


@router.callback_query(F.data == "yes_interested")
async def callback_yes_interested(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Да, интересно!'"""
    # Отправляем главное меню (шаг 6) с кнопками
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await callback.message.answer(step_6_text, reply_markup=menu_keyboard)
    await callback.answer()


@router.callback_query(F.data == "feedback")
async def callback_feedback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для 'Обратная связь'"""
    text = get_booking_text("feedback_request")
    feedback_buttons = {
        "Написать нам": "write_to_us_from_feedback",
        "<- Назад": "back_to_menu"
    }
    feedback_keyboard = await keyboard_ops.create_keyboard(buttons=feedback_buttons, interval=2)
    await callback.message.answer(text, reply_markup=feedback_keyboard)
    await callback.answer()


@router.callback_query(F.data == "write_to_us")
async def callback_write_to_us(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для 'Написать нам' из главного меню"""
    text = get_booking_text("write_to_us_request")
    back_buttons = {
        "<- Назад": "back_to_menu"
    }
    back_keyboard = await keyboard_ops.create_keyboard(buttons=back_buttons, interval=1)
    await callback.message.answer(text, reply_markup=back_keyboard)
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback.answer()


@router.callback_query(F.data == "write_to_us_from_feedback")
async def callback_write_to_us_from_feedback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для 'Написать нам' из экрана обратной связи"""
    # Ждем ввод от пользователя
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback.answer("Ожидаю ваше сообщение...")


@router.callback_query(F.data == "about_bot")
async def callback_about_bot(callback: CallbackQuery):
    """Обработчик callback для 'о боте'"""
    text = get_booking_text("about_bot")
    about_buttons = {
        "<- Назад": "back_to_menu",
        "Познакомиться ближе": "know_better"
    }
    about_keyboard = await keyboard_ops.create_keyboard(buttons=about_buttons, interval=2)
    await callback.message.answer(text, reply_markup=about_keyboard)
    await callback.answer()


@router.callback_query(F.data == "day_strategy")
async def callback_day_strategy(callback: CallbackQuery):
    """Обработчик callback для 'Стратегия дня'"""
    # Запускаем тот же процесс, что и "Познакомиться ближе"
    text = get_booking_text("know_better_first_time")
    await callback.message.answer(text)
    # Показываем второе сообщение о трех касаниях с кнопкой
    text_three_touches = get_booking_text("know_better_three_touches")
    understood_buttons = {
        "Понятно, идем дальше": "understood_move_on"
    }
    understood_keyboard = await keyboard_ops.create_keyboard(buttons=understood_buttons, interval=1)
    await callback.message.answer(text_three_touches, reply_markup=understood_keyboard)
    await callback.answer()


@router.callback_query(F.data == "bot_settings")
async def callback_bot_settings(callback: CallbackQuery):
    """Обработчик callback для 'Настройка бота'"""
    text = "Настройка бота"
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "my_subscription")
async def callback_my_subscription(callback: CallbackQuery):
    """Обработчик callback для 'Моя подписка'"""
    text = "Моя подписка"
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для кнопки 'Назад' - возврат в главное меню"""
    await state.clear()
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await callback.message.answer(step_6_text, reply_markup=menu_keyboard)
    await callback.answer()


@router.callback_query(F.data == "know_better")
async def callback_know_better(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Познакомиться ближе'"""
    # Запускаем тот же процесс, что и "Стратегия дня"
    text = get_booking_text("know_better_first_time")
    await callback.message.answer(text)
    # Показываем второе сообщение о трех касаниях с кнопкой
    text_three_touches = get_booking_text("know_better_three_touches")
    understood_buttons = {
        "Понятно, идем дальше": "understood_move_on"
    }
    understood_keyboard = await keyboard_ops.create_keyboard(buttons=understood_buttons, interval=1)
    await callback.message.answer(text_three_touches, reply_markup=understood_keyboard)
    await callback.answer()


@router.callback_query(F.data == "understood_move_on")
async def callback_understood_move_on(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Понятно, идем дальше'"""
    text = get_booking_text("notification_setup")
    menu_buttons = {
        "Главное меню": "back_to_menu",
        "Продолжить": "continue_after_notification"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await callback.message.answer(text, reply_markup=menu_keyboard)
    await callback.answer()


@router.callback_query(F.data == "continue_after_notification")
async def callback_continue_after_notification(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Продолжить' после настройки уведомлений"""
    text = get_booking_text("author_info")
    await callback.message.answer(text)
    
    # Показываем сообщение 7.8 с кнопками
    company_text = get_booking_text("company_info")
    company_buttons = {
        "👉 Переход в ТГ": "link_telegram",
        "👉 Переход в ВК": "link_vk",
        "Продолжить": "continue_after_company"
    }
    company_keyboard = await keyboard_ops.create_keyboard(buttons=company_buttons, interval=1)
    await callback.message.answer(company_text, reply_markup=company_keyboard)
    await callback.answer()


@router.callback_query(F.data == "link_telegram")
async def callback_link_telegram(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Переход в ТГ'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Ссылка на Telegram канал будет добавлена позже")


@router.callback_query(F.data == "link_vk")
async def callback_link_vk(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Переход в ВК'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Ссылка на ВК будет добавлена позже")


@router.callback_query(F.data == "continue_after_company")
async def callback_continue_after_company(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Продолжить' после информации о компании"""
    text = get_booking_text("course_intro")
    video_buttons = {
        "👉 Посмотреть видео": "watch_video",
        "Продолжить": "continue_after_video_intro"
    }
    video_keyboard = await keyboard_ops.create_keyboard(buttons=video_buttons, interval=2)
    await callback.message.answer(text, reply_markup=video_keyboard)
    await callback.answer()


@router.callback_query(F.data == "watch_video")
async def callback_watch_video(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Посмотреть видео'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Видео будет добавлено позже")


@router.callback_query(F.data == "continue_after_video_intro")
async def callback_continue_after_video_intro(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Продолжить' после введения в курс"""
    text = get_booking_text("after_video")
    payment_buttons = {
        "Оплата": "payment",
        "Подробнее": "more_details"
    }
    payment_keyboard = await keyboard_ops.create_keyboard(buttons=payment_buttons, interval=2)
    await callback.message.answer(text, reply_markup=payment_keyboard)
    await callback.answer()


@router.callback_query(F.data == "payment")
async def callback_payment(callback: CallbackQuery):
    """Обработчик callback для кнопки 'Оплата'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Оплата будет добавлена позже")


@router.callback_query(F.data == "more_details")
async def callback_more_details(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback для кнопки 'Подробнее'"""
    text = get_booking_text("quiz_start")
    await callback.message.answer(text)
    
    # Отправляем первый вопрос с кнопками 1-10
    question_1 = get_booking_text("quiz_question_1")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_1, reply_markup=rating_keyboard)
    
    # Устанавливаем состояние для первого вопроса
    await state.set_state(QuizStates.answering_question_1)
    await callback.answer()


def create_rating_keyboard():
    """Создает клавиатуру с кнопками 1-10 для оценки"""
    rating_buttons = {
        "1": "quiz_answer_1",
        "2": "quiz_answer_2",
        "3": "quiz_answer_3",
        "4": "quiz_answer_4",
        "5": "quiz_answer_5",
        "6": "quiz_answer_6",
        "7": "quiz_answer_7",
        "8": "quiz_answer_8",
        "9": "quiz_answer_9",
        "10": "quiz_answer_10"
    }
    return rating_buttons


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_1)
async def callback_quiz_answer_1(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на первый вопрос опроса (уровень энергии)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_1=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Переход ко второму вопросу
    question_2 = get_booking_text("quiz_question_2")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_2, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_2)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_2)
async def callback_quiz_answer_2(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на второй вопрос опроса (уровень счастья)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_2=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Переход к третьему вопросу
    question_3 = get_booking_text("quiz_question_3")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_3, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_3)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_3)
async def callback_quiz_answer_3(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на третий вопрос опроса (качество сна)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_3=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Переход к четвертому вопросу
    question_4 = get_booking_text("quiz_question_4")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_4, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_4)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_4)
async def callback_quiz_answer_4(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на четвертый вопрос опроса (качество значимых отношений)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_4=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Переход к пятому вопросу
    question_5 = get_booking_text("quiz_question_5")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_5, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_5)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_5)
async def callback_quiz_answer_5(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на пятый вопрос опроса (баланс жизни)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_5=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Переход к шестому вопросу
    question_6 = get_booking_text("quiz_question_6")
    rating_buttons = create_rating_keyboard()
    rating_keyboard = await keyboard_ops.create_keyboard(buttons=rating_buttons, interval=5)
    await callback.message.answer(question_6, reply_markup=rating_keyboard)
    await state.set_state(QuizStates.answering_question_6)


@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.answering_question_6)
async def callback_quiz_answer_6(callback: CallbackQuery, state: FSMContext):
    """Обработчик ответов на шестой вопрос опроса (личная стратегия)"""
    answer = callback.data.replace("quiz_answer_", "")
    await state.update_data(question_6=answer)
    await callback.answer(f"Вы выбрали: {answer}")
    
    # Опрос завершен, получаем все ответы
    data = await state.get_data()
    # Здесь можно сохранить результаты в БД
    
    # Показываем результат опроса
    result_text = get_booking_text("quiz_result")
    await callback.message.answer(result_text)
    
    # Здесь можно добавить отправку картинки с диаграммой позже
    # await callback.message.answer_photo(...)
    
    # Переходим к запросу вызовов
    challenges_text = get_booking_text("challenges_request")
    await callback.message.answer(challenges_text)
    await state.set_state(ProfileStates.waiting_for_challenges)


@router.callback_query(F.data == "edit_profile_data")
async def callback_edit_profile_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить' для редактирования данных профиля"""
    # Показываем вопрос "Что нужно изменить?"
    edit_text = get_booking_text("edit_question")
    edit_buttons = {
        "Цели": "edit_goals",
        "Вызовы": "edit_challenges"
    }
    edit_keyboard = await keyboard_ops.create_keyboard(buttons=edit_buttons, interval=2)
    await callback.message.answer(edit_text, reply_markup=edit_keyboard)
    await callback.answer()


@router.callback_query(F.data == "edit_challenges")
async def callback_edit_challenges(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Вызовы' для редактирования вызовов"""
    # Возвращаемся к запросу вызовов
    challenges_text = get_booking_text("challenges_request")
    await callback.message.answer(challenges_text)
    await state.set_state(ProfileStates.waiting_for_challenges)
    await callback.answer()


@router.callback_query(F.data == "edit_goals")
async def callback_edit_goals(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Цели' для редактирования целей"""
    # Возвращаемся к запросу целей
    goals_text = get_booking_text("goals_request")
    await callback.message.answer(goals_text)
    await state.set_state(ProfileStates.waiting_for_goals)
    await callback.answer()


@router.callback_query(F.data == "confirm_profile_data")
async def callback_confirm_profile_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Все верно' для подтверждения данных профиля"""
    # Получаем все данные
    data = await state.get_data()
    
    # Здесь можно сохранить данные в БД
    
    # Показываем выбор формата подписки
    subscription_text = get_booking_text("subscription_choice")
    subscription_buttons = {
        "Бесплатная неделя": "free_week",
        "Подписка на месяц": "monthly_subscription"
    }
    subscription_keyboard = await keyboard_ops.create_keyboard(buttons=subscription_buttons, interval=2)
    await callback.message.answer(subscription_text, reply_markup=subscription_keyboard)
    await callback.answer()


@router.callback_query(F.data == "free_week")
async def callback_free_week(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Пройти бесплатную неделю'"""
    # TODO: Проверить, понедельник ли сегодня (до 12 по МСК)
    # Если понедельник - пока ничего
    # Если не понедельник - показать сообщение 7.25.В
    
    # Пока всегда показываем сообщение готовности
    ready_text = get_booking_text("free_week_ready")
    await callback.message.answer(ready_text)
    
    # Показываем запрос согласия на обработку персональных данных
    consent_text = get_booking_text("personal_data_consent")
    consent_buttons = {
        "Далее": "consent_agree",
        "Не согласен": "consent_disagree"
    }
    consent_keyboard = await keyboard_ops.create_keyboard(buttons=consent_buttons, interval=2)
    await callback.message.answer(consent_text, reply_markup=consent_keyboard)
    await callback.answer()


@router.callback_query(F.data == "consent_disagree")
async def callback_consent_disagree(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Не согласен' - возврат в главное меню"""
    await state.clear()
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await callback.message.answer(step_6_text, reply_markup=menu_keyboard)
    await callback.answer()


@router.callback_query(F.data == "consent_agree")
async def callback_consent_agree(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Далее' - переход к запросу имени"""
    name_text = get_booking_text("name_request")
    await callback.message.answer(name_text)
    await state.set_state(ProfileStates.waiting_for_name)
    await callback.answer()


@router.callback_query(F.data == "username_confirm_yes")
async def callback_username_confirm_yes(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'ДА' для подтверждения ника"""
    # Переходим к запросу роли с кнопками
    role_text = get_booking_text("role_request")
    role_buttons = {
        "Собственник бизнеса": "role_business_owner",
        "СЕО": "role_ceo",
        "Топ-менеджер": "role_top_manager",
        "middle-руководитель": "role_middle_manager",
        "специалист": "role_specialist",
        "другое": "role_other"
    }
    role_keyboard = await keyboard_ops.create_keyboard(buttons=role_buttons, interval=2)
    await callback.message.answer(role_text, reply_markup=role_keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("role_"))
async def callback_role_selected(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора роли"""
    role_data = callback.data.replace("role_", "")
    
    if role_data == "other":
        # Запрашиваем ручной ввод роли
        await callback.message.answer("Напишите вашу профессиональную роль/должность:")
        await state.set_state(ProfileStates.waiting_for_role)
    else:
        # Сохраняем выбранную роль
        role_mapping = {
            "business_owner": "Собственник бизнеса",
            "ceo": "СЕО",
            "top_manager": "Топ-менеджер",
            "middle_manager": "middle-руководитель",
            "specialist": "специалист"
        }
        role = role_mapping.get(role_data, role_data)
        await state.update_data(role=role)
        
        # Переходим к запросу компании
        company_text = get_booking_text("company_request")
        await callback.message.answer(company_text)
        await state.set_state(ProfileStates.waiting_for_company)
    
    await callback.answer()


@router.callback_query(F.data == "username_confirm_no")
async def callback_username_confirm_no(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'НЕТ' для отказа от ника - возврат к запросу ника"""
    username_text = get_booking_text("username_request")
    await callback.message.answer(username_text)
    await state.set_state(ProfileStates.waiting_for_username)
    await callback.answer()


@router.callback_query(F.data == "edit_profile_personal_data")
async def callback_edit_profile_personal_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Изменить' для редактирования персональных данных"""
    # Показываем вопрос "Что нужно изменить?" с кнопками
    edit_text = get_booking_text("edit_field_question")
    edit_buttons = {
        "7.33 В ФИО": "edit_name",
        "7.33.Г Компания": "edit_company",
        "7.33.Д Должность": "edit_role"
    }
    edit_keyboard = await keyboard_ops.create_keyboard(buttons=edit_buttons, interval=1)
    await callback.message.answer(edit_text, reply_markup=edit_keyboard)
    await callback.answer()


@router.callback_query(F.data == "edit_name")
async def callback_edit_name(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'ФИО' для редактирования имени"""
    name_text = get_booking_text("edit_name_request")
    await callback.message.answer(name_text)
    await state.set_state(ProfileStates.editing_name)
    await callback.answer()


@router.callback_query(F.data == "edit_role")
async def callback_edit_role(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Должность' для редактирования роли"""
    role_text = get_booking_text("edit_role_request")
    await callback.message.answer(role_text)
    await state.set_state(ProfileStates.editing_role)
    await callback.answer()


@router.callback_query(F.data == "edit_company")
async def callback_edit_company(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Компания' для редактирования компании"""
    company_text = get_booking_text("edit_company_request")
    await callback.message.answer(company_text)
    await state.set_state(ProfileStates.editing_company)
    await callback.answer()


@router.callback_query(F.data == "confirm_profile_personal_data")
async def callback_confirm_profile_personal_data(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Верно' для подтверждения персональных данных"""
    # Получаем все данные
    data = await state.get_data()
    
    # TODO: Проверить, понедельник ли сегодня (до 12 по МСК)
    # Если понедельник - можно начинать курс
    # Если не понедельник - показать сообщение о начале новой недели
    
    # Здесь можно сохранить данные в БД
    
    # Показываем информацию о старте курса
    start_info_text = get_booking_text("course_start_info")
    start_buttons = {
        "7.35 ЧАТ ЕДИНОМЫШЛЕННИКОВ": "community_chat",
        "7.36 настроить уведомления от бота": "setup_notifications"
    }
    start_keyboard = await keyboard_ops.create_keyboard(buttons=start_buttons, interval=2)
    await callback.message.answer(start_info_text, reply_markup=start_keyboard)
    await callback.answer()


@router.callback_query(F.data == "community_chat")
async def callback_community_chat(callback: CallbackQuery):
    """Обработчик кнопки 'ЧАТ ЕДИНОМЫШЛЕННИКОВ'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Чат будет добавлен позже")


@router.callback_query(F.data == "setup_notifications")
async def callback_setup_notifications(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'настроить уведомления от бота' - возврат в главное меню"""
    await state.clear()
    step_6_text = get_booking_text("step_6")
    menu_buttons = {
        "Обратная связь": "feedback",
        "О боте": "about_bot",
        "Стратегия дня": "day_strategy",
        "Настройка бота": "bot_settings",
        "Моя подписка": "my_subscription"
    }
    menu_keyboard = await keyboard_ops.create_keyboard(buttons=menu_buttons, interval=2)
    await callback.message.answer(step_6_text, reply_markup=menu_keyboard)
    await callback.answer()


@router.callback_query(F.data == "monthly_subscription")
async def callback_monthly_subscription(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Подписка на месяц'"""
    # Заглушка - пока просто подтверждаем нажатие
    await callback.answer("Подписка на месяц будет добавлена позже")


