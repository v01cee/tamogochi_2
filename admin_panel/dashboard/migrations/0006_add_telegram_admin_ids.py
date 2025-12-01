# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_add_course_launch'),
    ]

    operations = [
        migrations.AddField(
            model_name='botsettings',
            name='telegram_admin_ids',
            field=models.TextField(blank=True, help_text='ID администраторов бота через запятую (например: 123456789,987654321). Получить свой ID можно через бота @userinfobot.', null=True, verbose_name='ID администраторов Telegram'),
        ),
    ]

