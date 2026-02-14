# check_database.py
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Database

print("🧪 Проверка базы данных...")

try:
    db = Database()

    # Печатаем всех пользователей
    print("\n👥 Все пользователи в системе:")
    users = db.get_all_users()

    if not users:
        print("📭 База данных пуста!")
    else:
        for user in users:
            user_id, fio, role = user
            print(f"  👤 {fio} (ID: {user_id}, Роль: {role})")

    # Проверяем работников
    print("\n👷 Работники в системе:")
    workers = db.get_all_workers()

    if not workers:
        print("📭 Нет работников!")
        print("\n⚠️ ПРОБЛЕМА: Чтобы кнопки 'Работники' и 'Отправить задание' работали,")
        print("нужно зарегистрировать хотя бы одного работника.")
        print("\n📋 Как добавить работника:")
        print("1. Открой Telegram в другом аккаунте (или используй @userinfobot для получения ID)")
        print("2. Найди бота @constructiondemo_bot")
        print("3. Нажми /start и зарегистрируйся")
        print("4. Вернись в админский аккаунт")
    else:
        print(f"✅ Найдено {len(workers)} работников:")
        for worker in workers:
            worker_id, fio = worker
            print(f"  👷 {fio} (ID: {worker_id})")

    # Проверяем таблицы
    print("\n📊 Структура базы данных:")
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    for table in tables:
        print(f"  📁 {table[0]}")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback

    traceback.print_exc()

print("\n✅ Проверка завершена")