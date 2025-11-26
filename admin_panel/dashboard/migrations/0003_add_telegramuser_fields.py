# Generated manually to sync model fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_alter_quizresult_options_alter_telegramuser_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='telegramuser',
            name='is_first_visit',
            field=models.BooleanField(default=True, verbose_name='Первый визит'),
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='notification_intro_seen',
            field=models.BooleanField(default=False, verbose_name='Видел вводное уведомление'),
        ),
    ]

