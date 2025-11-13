from django.db import models


class TelegramUser(models.Model):
    """Django-модель для работы с таблицей пользователей Telegram."""

    telegram_id = models.BigIntegerField("Telegram ID", unique=True, db_index=True)
    username = models.CharField("Никнейм", max_length=255, blank=True, null=True)
    first_name = models.CharField("Имя", max_length=255, blank=True, null=True)
    last_name = models.CharField("Фамилия", max_length=255, blank=True, null=True)
    language_code = models.CharField("Язык", max_length=10, blank=True, null=True)
    full_name = models.CharField("ФИО", max_length=255, blank=True, null=True)
    role = models.CharField("Должность/роль", max_length=255, blank=True, null=True)
    company = models.CharField("Компания", max_length=255, blank=True, null=True)
    subscription_type = models.CharField("Тип подписки", max_length=50, blank=True, null=True)
    subscription_started_at = models.DateTimeField("Подписка начата", blank=True, null=True)
    subscription_paid_at = models.DateTimeField("Оплата получена", blank=True, null=True)
    consent_accepted_at = models.DateTimeField("Согласие получено", blank=True, null=True)
    created_at = models.DateTimeField("Создан")
    updated_at = models.DateTimeField("Обновлён")
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        managed = False
        db_table = "users"
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"

    def __str__(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or str(self.telegram_id)


class QuizResult(models.Model):
    """Результаты стартового опроса."""

    user = models.ForeignKey(
        TelegramUser,
        related_name="quiz_results",
        on_delete=models.DO_NOTHING,
        db_column="user_id",
        verbose_name="Пользователь",
    )
    energy = models.PositiveSmallIntegerField("Энергия")
    happiness = models.PositiveSmallIntegerField("Счастье")
    sleep_quality = models.PositiveSmallIntegerField("Сон")
    relationships_quality = models.PositiveSmallIntegerField("Отношения")
    life_balance = models.PositiveSmallIntegerField("Баланс")
    strategy_level = models.PositiveSmallIntegerField("Стратегия")
    created_at = models.DateTimeField("Создан")
    updated_at = models.DateTimeField("Обновлён")
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        managed = False
        db_table = "quiz_results"
        verbose_name = "Результат опроса"
        verbose_name_plural = "Результаты опроса"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Опрос {self.user} от {self.created_at:%d.%m.%Y %H:%M}"


class CourseDay(models.Model):
    """День курса."""

    day_number = models.PositiveIntegerField("День", unique=True)
    title = models.CharField("Название", max_length=255)
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField("Обновлён", auto_now=True, editable=False)

    class Meta:
        managed = False
        db_table = "course_days"
        verbose_name = "День курса"
        verbose_name_plural = "Дни курса"
        ordering = ("day_number",)

    def __str__(self) -> str:
        return f"День {self.day_number}: {self.title}"


class TouchContent(models.Model):
    """Контент для касаний."""

    TOUCH_TYPES = (
        ("morning", "Утро"),
        ("day", "День"),
        ("evening", "Вечер"),
    )

    course_day = models.ForeignKey(
        CourseDay,
        verbose_name="День курса",
        related_name="touches",
        on_delete=models.DO_NOTHING,
        db_column="course_day_id",
        blank=True,
        null=True,
    )
    touch_type = models.CharField("Тип касания", max_length=20, choices=TOUCH_TYPES)
    step_code = models.CharField("Код шага", max_length=50, unique=True, blank=True, null=True)
    title = models.CharField("Заголовок", max_length=255)
    video_file = models.FileField(
        "Видео-файл",
        upload_to="touch_videos/",
        blank=True,
        null=True,
        db_column="video_file_path",
    )
    video_url = models.URLField("Ссылка на видео", max_length=500, blank=True, null=True)
    summary = models.TextField("Описание", blank=True, null=True)
    transcript = models.TextField("Расшифровка", blank=True, null=True)
    questions = models.TextField("Вопросы (писать через пропуск строки)", blank=True, null=True)
    is_active = models.BooleanField("Активно", default=True)
    order_index = models.IntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField("Обновлён", auto_now=True, editable=False)

    class Meta:
        managed = False
        db_table = "touch_contents"
        verbose_name = "Контент касания"
        verbose_name_plural = "Контент касаний"
        ordering = ("course_day__day_number", "touch_type", "order_index")

    def __str__(self) -> str:
        day = f"{self.course_day}" if self.course_day else "Без дня"
        return f"{day} | {self.get_touch_type_display()} | {self.title}"


