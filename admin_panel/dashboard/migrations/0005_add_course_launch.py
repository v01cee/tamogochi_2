# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_add_bot_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseLaunch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('launch_date', models.DateTimeField(help_text='Дата следующего понедельника, с которого начнется рассылка касаний', verbose_name='Дата запуска процесса')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='Процесс запущен')),
                ('started_by', models.CharField(blank=True, max_length=255, null=True, verbose_name='Запустил')),
                ('users_count', models.IntegerField(default=0, verbose_name='Количество пользователей')),
                ('is_active', models.BooleanField(default=True, help_text='Только один активный запуск может быть', verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлён')),
            ],
            options={
                'verbose_name': 'Запуск курса',
                'verbose_name_plural': 'Запуски курса',
                'db_table': 'course_launches',
                'managed': True,
                'ordering': ('-started_at',),
            },
        ),
    ]

