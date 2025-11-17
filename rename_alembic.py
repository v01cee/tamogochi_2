import os
import shutil

# Переименовываем папку alembic в migrations
current_dir = '.'
alembic_path = os.path.join(current_dir, 'alembic')
migrations_path = os.path.join(current_dir, 'migrations')

if os.path.exists(alembic_path) and os.path.isdir(alembic_path):
    if os.path.exists(migrations_path):
        print(f"Папка 'migrations' уже существует! Удалите её или переименуйте вручную.")
    else:
        print(f"Переименовываю 'alembic' в 'migrations'...")
        os.rename(alembic_path, migrations_path)
        print(f"Готово! Папка переименована в 'migrations'")
elif os.path.exists(migrations_path):
    print(f"Папка 'migrations' уже существует!")
else:
    print(f"Папка 'alembic' не найдена!")

