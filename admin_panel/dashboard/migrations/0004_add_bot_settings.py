# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_add_telegramuser_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_group_id', models.BigIntegerField(blank=True, help_text='ID группы/канала в Telegram, куда будут пересылаться сообщения обратной связи', null=True, verbose_name='ID группы для обратной связи')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
            ],
            options={
                'verbose_name': 'Настройки бота',
                'verbose_name_plural': 'Настройки бота',
                'db_table': 'bot_settings',
                'managed': True,
            },
        ),
    ]

