from aiogram.fsm.state import State, StatesGroup


class FeedbackStates(StatesGroup):
    """Состояния для обратной связи"""
    waiting_for_feedback = State()


class QuizStates(StatesGroup):
    """Состояния для опроса"""
    answering_question_1 = State()  # Оценка уровня энергии
    answering_question_2 = State()
    answering_question_3 = State()
    answering_question_4 = State()
    answering_question_5 = State()
    answering_question_6 = State()


class ProfileStates(StatesGroup):
    """Состояния для заполнения профиля"""
    waiting_for_challenges = State()  # Ожидание вызовов
    waiting_for_goals = State()  # Ожидание целей
    waiting_for_name = State()  # Ожидание имени и фамилии
    waiting_for_username = State()  # Ожидание ника в Telegram
    waiting_for_role = State()  # Ожидание роли (если выбрано "другое")
    waiting_for_company = State()  # Ожидание компании
    editing_name = State()  # Редактирование имени
    editing_role = State()  # Редактирование роли
    editing_company = State()  # Редактирование компании


class NotificationSettingsStates(StatesGroup):
    """Состояния для настройки уведомлений"""
    choosing_touch = State()
    waiting_for_time = State()

