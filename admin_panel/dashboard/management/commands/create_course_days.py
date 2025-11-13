"""
Django management команда для создания 24 дней курса.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Создаёт 24 дня курса в базе данных"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Проверяем, есть ли уже дни
            cursor.execute("SELECT COUNT(*) FROM course_days")
            count = cursor.fetchone()[0]
            
            if count > 0:
                self.stdout.write(
                    self.style.WARNING(f"В базе уже есть {count} дней курса. Пропускаем создание.")
                )
                return
            
            # Создаём 24 дня
            days_data = []
            for day_num in range(1, 25):
                title = f"День {day_num}"
                days_data.append((day_num, title))
            
            # Вставляем данные
            cursor.executemany(
                """
                INSERT INTO course_days (day_number, title, is_active, created_at, updated_at)
                VALUES (%s, %s, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                days_data
            )
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ Успешно создано {len(days_data)} дней курса!")
            )

