# handlers/worker.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import sys
import os

# Добавляем корень проекта в путь Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from database import Database
from keyboards import (
    get_main_keyboard,
    get_task_actions_keyboard,
    get_back_to_menu_keyboard
)
from states.worker_states import WorkerStates
from config import Config
from datetime import datetime

router = Router()
db = Database()

print("🔍 WORKER HANDLER: Инициализация...")


# --- Регистрация пользователя ---
@router.message(WorkerStates.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    """Обработка ввода ФИО при регистрации"""
    print(f"🔍 WORKER: process_fio вызван! Текст: {message.text}")

    fio = message.text.strip()
    user_id = message.from_user.id
    username = message.from_user.username or ""

    if len(fio) < 2:
        await message.answer("❌ ФИО слишком короткое. Введите полное имя:")
        return

    # Сохраняем пользователя в БД
    db.add_user(user_id, username, fio)
    print(f"🔍 WORKER: Пользователь сохранен: user_id={user_id}, fio={fio}")

    # Получаем обновленные данные
    user = db.get_user(user_id)
    role = user[3] if user else 'worker'

    # Очищаем состояние
    await state.clear()
    print(f"🔍 WORKER: Состояние очищено, роль: {role}")

    # Приветствуем в зависимости от роли
    if role == 'admin':
        await message.answer(
            f"👑 Здравствуйте, администратор {fio}!",
            reply_markup=get_main_keyboard('admin')
        )
    else:
        await message.answer(
            f"👷 Добро пожаловать, {fio}! Теперь вы можете работать с заданиями.",
            reply_markup=get_main_keyboard('worker')
        )


# --- Мои задания (работник) ---
@router.message(F.text == "📋 Мои задания")
async def show_my_tasks(message: types.Message):
    """Показать задания работника"""
    print(f"🔍 WORKER: Кнопка '📋 Мои задания' нажата user_id={message.from_user.id}")

    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        print(f"🔍 WORKER: Пользователь {user_id} не найден в БД")
        await message.answer("Сначала зарегистрируйтесь через /start")
        return

    print(f"🔍 WORKER: Пользователь найден: {user['fio']}")

    # Получаем задания
    tasks = db.get_worker_tasks(user_id)
    print(f"🔍 WORKER: Получено {len(tasks)} заданий для user_id={user_id}")

    if not tasks:
        await message.answer("📭 У вас пока нет заданий.")
        return

    for task in tasks:
        task_id = task['task_id']
        task_text = task['task_text']
        status = task['status']
        created_at = task['created_at']
        comment = task['worker_comment']

        status_text = {
            'pending': '⏳ Ожидает принятия',
            'accepted': '✅ Принято',
            'completed': '✅ Выполнено',
            'commented': '📝 С комментарием'
        }.get(status, status)

        task_message = f"""
📋 **Задание #{task_id}**
──────────────
{task_text}
──────────────
📊 **Статус:** {status_text}
📅 **Создано:** {created_at}
        """

        if status == 'pending':
            # Отправляем задание с кнопками действий
            print(f"🔍 WORKER: Отправляю задание #{task_id} с кнопками действий")
            await message.answer(
                task_message,
                reply_markup=get_task_actions_keyboard(task_id)
            )
        else:
            # Отправляем только информацию о задании
            if comment and status == 'commented':
                task_message += f"\n📝 **Комментарий:** {comment}"

            await message.answer(task_message)


# --- Принятие задания ---
@router.callback_query(F.data.startswith("accept_task:"))
async def accept_task(callback: types.CallbackQuery):
    """Обработка принятия задания"""
    print(f"🔍 WORKER CALLBACK: accept_task вызван, data={callback.data}")

    task_id = int(callback.data.split(":")[1])
    print(f"🔍 WORKER: Принимаем задание #{task_id}")

    # Обновляем статус задания
    db.update_task_status(task_id, "accepted")

    # Получаем информацию о задании
    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT at.*, u.fio as worker_fio, admin_user.fio as admin_fio
    FROM admin_tasks at
    JOIN users u ON at.to_worker_id = u.user_id
    JOIN users admin_user ON at.from_admin_id = admin_user.user_id
    WHERE at.task_id = ?
    ''', (task_id,))
    task = cursor.fetchone()

    if task:
        # Уведомляем администратора
        admin_id = task['from_admin_id']
        worker_fio = task['worker_fio']
        task_text = task['task_text']

        notification = f"""
✅ **Задание принято!**
──────────────
**Работник:** {worker_fio}
**Задание:** {task_text}
**Время:** {datetime.now().strftime('%H:%M %d.%m.%Y')}
        """

        try:
            await callback.message.bot.send_message(
                admin_id,
                notification
            )
            print(f"🔍 WORKER: Уведомление отправлено администратору {admin_id}")
        except Exception as e:
            print(f"🔍 WORKER: Ошибка отправки уведомления администратору: {e}")

    await callback.answer("✅ Задание принято!")
    await callback.message.edit_text(
        f"✅ Вы приняли задание #{task_id}",
        reply_markup=None
    )


# --- Комментарий к заданию ---
@router.callback_query(F.data.startswith("comment_task:"))
async def comment_task(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса комментирования задания"""
    print(f"🔍 WORKER CALLBACK: comment_task вызван, data={callback.data}")

    task_id = int(callback.data.split(":")[1])

    # Сохраняем task_id в состоянии
    await state.update_data(task_id=task_id)
    await state.set_state(WorkerStates.waiting_for_comment)

    await callback.message.edit_text(
        f"📝 Напишите причину, почему не можете принять задание #{task_id}:",
        reply_markup=None
    )

    await callback.answer()


@router.message(WorkerStates.waiting_for_comment)
async def process_task_comment(message: types.Message, state: FSMContext):
    """Обработка комментария к заданию"""
    print(f"🔍 WORKER: process_task_comment вызван, текст: {message.text}")

    comment = message.text.strip()
    data = await state.get_data()
    task_id = data.get('task_id')

    if not task_id:
        await message.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()
        return

    # Обновляем задание с комментарием
    db.update_task_status(task_id, "commented", comment)

    # Получаем информацию о задании
    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT at.*, u.fio as worker_fio, admin_user.fio as admin_fio
    FROM admin_tasks at
    JOIN users u ON at.to_worker_id = u.user_id
    JOIN users admin_user ON at.from_admin_id = admin_user.user_id
    WHERE at.task_id = ?
    ''', (task_id,))
    task = cursor.fetchone()

    if task:
        # Уведомляем администратора
        admin_id = task['from_admin_id']
        worker_fio = task['worker_fio']
        task_text = task['task_text']

        notification = f"""
📝 **Комментарий к заданию**
──────────────
**Работник:** {worker_fio}
**Задание:** {task_text}
**Комментарий:** {comment}
**Время:** {datetime.now().strftime('%H:%M %d.%m.%Y')}
        """

        try:
            await message.bot.send_message(
                admin_id,
                notification
            )
            print(f"🔍 WORKER: Комментарий отправлен администратору {admin_id}")
        except Exception as e:
            print(f"🔍 WORKER: Ошибка отправки комментария администратору: {e}")

    await message.answer(
        f"📝 Ваш комментарий к заданию #{task_id} отправлен администратору.",
        reply_markup=get_main_keyboard('worker')
    )

    await state.clear()


# --- Создание задания работником ---
@router.message(F.text == "📝 Создать задание")
async def create_worker_task(message: types.Message, state: FSMContext):
    """Начало создания задания работником"""
    print(f"🔍 WORKER: Кнопка '📝 Создать задание' нажата user_id={message.from_user.id}")

    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user:
        await message.answer("Сначала зарегистрируйтесь через /start")
        return

    await message.answer(
        "📝 Введите текст задания, которое хотите отправить на согласование администратору:",
        reply_markup=get_back_to_menu_keyboard()
    )

    await state.set_state(WorkerStates.waiting_for_task_text)


@router.message(WorkerStates.waiting_for_task_text)
async def process_worker_task_text(message: types.Message, state: FSMContext):
    """Обработка текста задания от работника"""
    print(f"🔍 WORKER: process_worker_task_text вызван, текст: {message.text}")

    task_text = message.text.strip()
    user_id = message.from_user.id

    if len(task_text) < 5:
        await message.answer("❌ Текст задания слишком короткий. Введите подробнее:")
        return

    # Сохраняем задание в БД
    task_id = db.add_worker_task(user_id, task_text)
    print(f"🔍 WORKER: Задание #{task_id} сохранено в БД")

    # Получаем информацию о работнике
    user = db.get_user(user_id)
    worker_fio = user[2] if user else "Неизвестный"

    # Уведомляем всех администраторов
    admin_ids = Config.get_admin_ids()
    print(f"🔍 WORKER: Отправляю уведомления администраторам: {admin_ids}")

    for admin_id in admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"""
📝 **Новый запрос от работника**
──────────────
**От:** {worker_fio}
**Задание:** {task_text}
**ID запроса:** #{task_id}
                """
            )
            print(f"🔍 WORKER: Уведомление отправлено администратору {admin_id}")
        except Exception as e:
            print(f"🔍 WORKER: Ошибка отправки администратору {admin_id}: {e}")

    await message.answer(
        f"✅ Ваше задание #{task_id} отправлено на согласование администратору.",
        reply_markup=get_main_keyboard('worker')
    )

    await state.clear()


# --- Статус запросов работника ---
@router.message(F.text == "📊 Статус запросов")
async def show_worker_requests(message: types.Message):
    """Показать статус заданий, отправленных работником"""
    print(f"🔍 WORKER: Кнопка '📊 Статус запросов' нажата user_id={message.from_user.id}")

    user_id = message.from_user.id

    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT wt.*, u.fio as reviewer_fio
    FROM worker_tasks wt
    LEFT JOIN users u ON wt.reviewed_by = u.user_id
    WHERE wt.from_worker_id = ?
    ORDER BY wt.created_at DESC
    ''', (user_id,))

    tasks = cursor.fetchall()
    print(f"🔍 WORKER: Получено {len(tasks)} заданий от работника")

    if not tasks:
        await message.answer("📭 Вы еще не отправляли заданий на согласование.")
        return

    for task in tasks:
        task_id = task['task_id']
        task_text = task['task_text']
        status = task['status']
        created_at = task['created_at']
        reviewed_at = task['reviewed_at']
        admin_comment = task['admin_comment']
        reviewer_fio = task['reviewer_fio']

        status_text = {
            'pending': '⏳ На рассмотрении',
            'approved': '✅ Одобрено',
            'rejected': '❌ Отклонено'
        }.get(status, status)

        task_message = f"""
📋 **Мой запрос #{task_id}**
──────────────
{task_text}
──────────────
📊 **Статус:** {status_text}
📅 **Отправлено:** {created_at}
        """

        if status in ['approved', 'rejected'] and reviewed_at:
            task_message += f"\n📅 **Рассмотрено:** {reviewed_at}"
            if reviewer_fio:
                task_message += f"\n👤 **Рассмотрел:** {reviewer_fio}"

        if admin_comment:
            task_message += f"\n💬 **Комментарий:** {admin_comment}"

        await message.answer(task_message)


