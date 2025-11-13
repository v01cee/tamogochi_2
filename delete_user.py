"""Скрипт для удаления пользователя из базы данных"""
import sys
from database.session import get_session
from repositories.user_repository import UserRepository

def delete_user(telegram_id: int):
    """Удалить пользователя по Telegram ID"""
    session = next(get_session())
    try:
        user_repo = UserRepository(session)
        user = user_repo.get_by_telegram_id(telegram_id)
        
        if not user:
            print(f"Пользователь с Telegram ID {telegram_id} не найден")
            return False
        
        print(f"Найден пользователь: {user.username or user.first_name} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        
        confirm = input("Вы уверены, что хотите удалить этого пользователя? (yes/no): ")
        if confirm.lower() != "yes":
            print("Удаление отменено")
            return False
        
        user_repo.delete(user.id, soft=False)  # hard delete
        print(f"Пользователь {telegram_id} успешно удален")
        return True
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python delete_user.py <telegram_id>")
        print("Пример: python delete_user.py 123456789")
        sys.exit(1)
    
    try:
        telegram_id = int(sys.argv[1])
        delete_user(telegram_id)
    except ValueError:
        print("Ошибка: Telegram ID должен быть числом")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при удалении пользователя: {e}")
        sys.exit(1)

