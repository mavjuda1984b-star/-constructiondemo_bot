# database.py
import sqlite3
from datetime import datetime
from config import Config


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Убираем префикс sqlite:/// для пути к файлу
            db_path = Config.DATABASE_URL.replace('sqlite:///', '')
            print(f"🔍 DATABASE: Используем БД: {db_path}")

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Для доступа по имени столбца
        self.create_tables()

    def create_tables(self):
        """Создаем таблицы в базе данных"""
        cursor = self.conn.cursor()

        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            fio TEXT NOT NULL,
            role TEXT DEFAULT 'worker',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица заданий от администратора
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_admin_id INTEGER NOT NULL,
            to_worker_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, accepted, completed, commented
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            read_at TIMESTAMP,
            completed_at TIMESTAMP,
            worker_comment TEXT,
            FOREIGN KEY (to_worker_id) REFERENCES users (user_id),
            FOREIGN KEY (from_admin_id) REFERENCES users (user_id)
        )
        ''')

        # Таблица заданий от работников
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_worker_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            admin_comment TEXT,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            FOREIGN KEY (from_worker_id) REFERENCES users (user_id),
            FOREIGN KEY (reviewed_by) REFERENCES users (user_id)
        )
        ''')

        # Таблица уведомлений
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')

        self.conn.commit()
        print("🔍 DATABASE: Таблицы созданы/проверены")

    def add_user(self, user_id: int, username: str, fio: str):
        """Добавляем пользователя в БД"""
        cursor = self.conn.cursor()

        # Проверяем, админ ли это
        role = 'admin' if Config.is_admin(user_id) else 'worker'
        print(f"🔍 DATABASE: add_user - user_id={user_id}, fio={fio}, role={role}")

        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, fio, role)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, fio, role))

        self.conn.commit()
        print(f"🔍 DATABASE: Пользователь {fio} добавлен с ролью {role}")

    def get_user(self, user_id: int):
        """Получаем данные пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()

        if user:
            print(f"🔍 DATABASE: get_user найден: user_id={user_id}, fio={user['fio']}, role={user['role']}")
        else:
            print(f"🔍 DATABASE: get_user не найден: user_id={user_id}")

        return user

    def get_all_workers(self):
        """Получаем всех работников (не админов)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id, fio FROM users WHERE role = ? ORDER BY fio', ('worker',))
        workers = cursor.fetchall()

        print(f"🔍 DATABASE: get_all_workers вернул {len(workers)} работников")
        for worker in workers:
            print(f"  - ID: {worker[0]}, ФИО: {worker[1]}")

        return workers

    def get_all_users(self):
        """Получаем всех пользователей"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT user_id, fio, role FROM users ORDER BY role, fio')
        users = cursor.fetchall()

        print(f"🔍 DATABASE: get_all_users вернул {len(users)} пользователей")
        return users

    def add_admin_task(self, from_admin_id: int, to_worker_id: int, task_text: str):
        """Добавляем задание от администратора"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO admin_tasks (from_admin_id, to_worker_id, task_text)
        VALUES (?, ?, ?)
        ''', (from_admin_id, to_worker_id, task_text))
        self.conn.commit()
        task_id = cursor.lastrowid

        print(f"🔍 DATABASE: add_admin_task - task_id={task_id}, от админа {from_admin_id} работнику {to_worker_id}")
        return task_id

    def get_worker_tasks(self, worker_id: int, status: str = None):
        """Получаем задания для работника"""
        cursor = self.conn.cursor()
        if status:
            cursor.execute('''
            SELECT * FROM admin_tasks 
            WHERE to_worker_id = ? AND status = ?
            ORDER BY created_at DESC
            ''', (worker_id, status))
        else:
            cursor.execute('''
            SELECT * FROM admin_tasks 
            WHERE to_worker_id = ?
            ORDER BY created_at DESC
            ''', (worker_id,))

        tasks = cursor.fetchall()
        print(f"🔍 DATABASE: get_worker_tasks для worker_id={worker_id} вернул {len(tasks)} заданий")
        return tasks

    def update_task_status(self, task_id: int, status: str, comment: str = None):
        """Обновляем статус задания"""
        cursor = self.conn.cursor()
        if comment:
            cursor.execute('''
            UPDATE admin_tasks 
            SET status = ?, worker_comment = ?, read_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
            ''', (status, comment, task_id))
            print(f"🔍 DATABASE: update_task_status task_id={task_id} -> {status} с комментарием")
        else:
            cursor.execute('''
            UPDATE admin_tasks 
            SET status = ?, read_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
            ''', (status, task_id))
            print(f"🔍 DATABASE: update_task_status task_id={task_id} -> {status}")

        self.conn.commit()

    def add_worker_task(self, from_worker_id: int, task_text: str):
        """Добавляем задание от работника"""
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO worker_tasks (from_worker_id, task_text)
        VALUES (?, ?)
        ''', (from_worker_id, task_text))
        self.conn.commit()
        task_id = cursor.lastrowid

        print(f"🔍 DATABASE: add_worker_task - task_id={task_id}, от работника {from_worker_id}")
        return task_id

    def get_pending_worker_tasks(self):
        """Получаем все задания от работников на рассмотрении"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT wt.*, u.fio 
        FROM worker_tasks wt
        JOIN users u ON wt.from_worker_id = u.user_id
        WHERE wt.status = 'pending'
        ORDER BY wt.created_at ASC
        ''')

        tasks = cursor.fetchall()
        print(f"🔍 DATABASE: get_pending_worker_tasks вернул {len(tasks)} заданий на рассмотрении")
        return tasks

    def update_worker_task_status(self, task_id: int, status: str, admin_id: int, comment: str = None):
        """Обновляем статус задания от работника"""
        cursor = self.conn.cursor()
        if comment:
            cursor.execute('''
            UPDATE worker_tasks 
            SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP, admin_comment = ?
            WHERE task_id = ?
            ''', (status, admin_id, comment, task_id))
            print(f"🔍 DATABASE: update_worker_task_status task_id={task_id} -> {status} с комментарием")
        else:
            cursor.execute('''
            UPDATE worker_tasks 
            SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
            ''', (status, admin_id, task_id))
            print(f"🔍 DATABASE: update_worker_task_status task_id={task_id} -> {status}")

        self.conn.commit()

    def close(self):
        """Закрываем соединение с БД"""
        self.conn.close()
        print("🔍 DATABASE: Соединение закрыто")

    # Дополнительный метод для отладки
    def print_all_users(self):
        """Выводим всех пользователей для отладки"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()

        print("\n" + "=" * 50)
        print("📊 ВСЕ ПОЛЬЗОВАТЕЛИ В БАЗЕ ДАННЫХ:")
        print("=" * 50)

        if not users:
            print("📭 База данных пуста")
        else:
            for user in users:
                print(f"ID: {user['user_id']}")
                print(f"  ФИО: {user['fio']}")
                print(f"  Роль: {user['role']}")
                print(f"  Username: {user['username']}")
                print(f"  Зарегистрирован: {user['registered_at']}")
                print("-" * 30)

        print(f"Всего пользователей: {len(users)}")
        print("=" * 50)