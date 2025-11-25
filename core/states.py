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


class TouchQuestionStates(StatesGroup):
    """Состояния для ответов на вопросы касания"""
    waiting_for_answer = State()  # Ожидание ответа на вопрос касания
    waiting_for_voice_confirmation = State()  # Ожидание подтверждения голосового сообщения


class EveningRatingStates(StatesGroup):
    """Состояния для вечерней оценки"""
    rating_energy = State()  # Оценка уровня энергии (1/5)
    rating_happiness = State()  # Оценка уровня счастья (2/5)
    rating_progress = State()  # Оценка продвижения к результату/целям (3/5)
    rating_question_4 = State()  # Вопрос 4/5
    rating_question_5 = State()  # Вопрос 5/5


class SaturdayReflectionStates(StatesGroup):
    """Состояния для рефлексии стратсубботы"""
    answering_segment_1 = State()  # 1/5 Похвастаться
    answering_segment_2 = State()  # 2/5 Что не получилось
    answering_segment_3 = State()  # 3/5 Поблагодарить
    answering_segment_4 = State()  # 4/5 Помечтать
    answering_segment_5 = State()  # 5/5 Пообещать
    confirming_segment_1 = State()  # Подтверждение сегмента 1
    confirming_segment_2 = State()  # Подтверждение сегмента 2
    confirming_segment_3 = State()  # Подтверждение сегмента 3
    confirming_segment_4 = State()  # Подтверждение сегмента 4
    confirming_segment_5 = State()  # Подтверждение сегмента 5