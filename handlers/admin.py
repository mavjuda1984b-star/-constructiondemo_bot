# handlers/admin.py - УПРОЩЕННАЯ ВЕРСИЯ БЕЗ ДЕКОРАТОРА
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
    get_workers_keyboard,
    get_worker_task_review_keyboard,
    get_back_to_menu_keyboard
)
from states.admin_states import AdminStates
from config import Config
from datetime import datetime

router = Router()
db = Database()


# --- Вспомогательная функция для проверки админа ---
def check_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    is_admin = Config.is_admin(user_id)
    print(f"🔍 CHECK ADMIN: user_id={user_id}, is_admin={is_admin}")
    return is_admin


# --- Список работников ---
@router.message(F.text == "👥 Работники")
async def show_workers(message: types.Message):
    """Показать список всех работников"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    print(f"🔍 ADMIN: Кнопка 'Работники' нажата user_id={message.from_user.id}")

    users = db.get_all_users()

    if not users:
        await message.answer("📭 В системе еще нет работников.")
        return

    admin_count = 0
    worker_count = 0
    workers_list = []

    response = "👥 **Список пользователей:**\n\n"

    for user in users:
        user_id, fio, role = user
        role_emoji = "👑" if role == 'admin' else "👷"

        response += f"{role_emoji} **{fio}**\n"
        response += f"   ID: {user_id}\n"
        response += f"   Роль: {role}\n\n"

        if role == 'admin':
            admin_count += 1
        else:
            worker_count += 1
            workers_list.append((user_id, fio))

    response += f"📊 **Итого:** {admin_count} администраторов, {worker_count} работников"

    await message.answer(response)


# --- Отправка задания работнику ---
@router.message(F.text == "📨 Отправить задание")
async def send_task_to_worker(message: types.Message, state: FSMContext):
    """Начало процесса отправки задания"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    print(f"🔍 ADMIN: Кнопка 'Отправить задание' нажата user_id={message.from_user.id}")

    workers = db.get_all_workers()

    if not workers:
        await message.answer("📭 В системе нет работников.")
        return

    await message.answer(
        "👷 Выберите работника, которому хотите отправить задание:",
        reply_markup=get_workers_keyboard(workers)
    )

    await state.set_state(AdminStates.waiting_for_worker_selection)


@router.callback_query(F.data.startswith("select_worker:"), AdminStates.waiting_for_worker_selection)
async def select_worker(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора работника"""
    user_id = callback.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await callback.answer("⛔ У вас нет прав администратора!", show_alert=True)
        return

    print(f"🔍 ADMIN CALLBACK: select_worker вызван, data={callback.data}")

    worker_id = int(callback.data.split(":")[1])

    # Получаем информацию о работнике
    worker = db.get_user(worker_id)
    if not worker:
        await callback.answer("❌ Работник не найден")
        return

    worker_fio = worker[2]

    # Сохраняем worker_id в состоянии
    await state.update_data(worker_id=worker_id, worker_fio=worker_fio)
    await state.set_state(AdminStates.waiting_for_task_text)

    await callback.message.edit_text(
        f"👷 Выбран работник: {worker_fio}\n\n"
        f"✏️ Теперь введите текст задания:",
        reply_markup=None
    )

    await callback.answer()


@router.message(AdminStates.waiting_for_task_text)
async def process_admin_task_text(message: types.Message, state: FSMContext):
    """Обработка текста задания от администратора"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    task_text = message.text.strip()
    data = await state.get_data()
    worker_id = data.get('worker_id')
    worker_fio = data.get('worker_fio')
    admin_id = message.from_user.id

    if len(task_text) < 5:
        await message.answer("❌ Текст задания слишком короткий. Введите подробнее:")
        return

    # Сохраняем задание в БД
    task_id = db.add_admin_task(admin_id, worker_id, task_text)

    # Получаем информацию об администраторе
    admin_user = db.get_user(admin_id)
    admin_fio = admin_user[2] if admin_user else "Администратор"

    # Отправляем задание работнику
    task_message = f"""
📋 **Новое задание от администратора!**
──────────────
{task_text}
──────────────
📅 **Отправлено:** {datetime.now().strftime('%H:%M %d.%m.%Y')}
👑 **От:** {admin_fio}
🆔 **ID задания:** #{task_id}
    """

    try:
        await message.bot.send_message(
            worker_id,
            task_message,
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="✅ ПРИНЯТЬ",
                            callback_data=f"accept_task:{task_id}"
                        )
                    ],
                    [
                        types.InlineKeyboardButton(
                            text="📝 КОММЕНТАРИЙ",
                            callback_data=f"comment_task:{task_id}"
                        )
                    ]
                ]
            )
        )

        await message.answer(
            f"✅ Задание #{task_id} отправлено работнику {worker_fio}",
            reply_markup=get_main_keyboard('admin')
        )
    except Exception as e:
        await message.answer(
            f"❌ Не удалось отправить задание работнику {worker_fio}. "
            f"Возможно, он не начал диалог с ботом.\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=get_main_keyboard('admin')
        )

    await state.clear()


# --- Запросы от работников ---
@router.message(F.text == "✅ Запросы от работников")
async def show_worker_requests_admin(message: types.Message):
    """Показать задания от работников на рассмотрении"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    print(f"🔍 ADMIN: Кнопка 'Запросы от работников' нажата")

    tasks = db.get_pending_worker_tasks()

    if not tasks:
        await message.answer("📭 Нет заданий от работников на рассмотрении.")
        return

    await message.answer(f"📝 Заданий на рассмотрении: {len(tasks)}")

    for task in tasks:
        task_id = task['task_id']
        task_text = task['task_text']
        created_at = task['created_at']
        worker_fio = task['fio']

        task_message = f"""
📋 **Запрос #{task_id}**
──────────────
**От:** {worker_fio}
**Задание:** {task_text}
**Время:** {created_at}
        """

        await message.answer(
            task_message,
            reply_markup=get_worker_task_review_keyboard(task_id)
        )


# --- Одобрение задания от работника ---
@router.callback_query(F.data.startswith("approve_task:"))
async def approve_worker_task(callback: types.CallbackQuery):
    """Одобрение задания от работника"""
    user_id = callback.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await callback.answer("⛔ У вас нет прав администратора!", show_alert=True)
        return

    task_id = int(callback.data.split(":")[1])
    admin_id = callback.from_user.id

    # Обновляем статус задания
    db.update_worker_task_status(task_id, "approved", admin_id)

    # Получаем информацию о задании
    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT wt.*, u.user_id as worker_id, u.fio as worker_fio
    FROM worker_tasks wt
    JOIN users u ON wt.from_worker_id = u.user_id
    WHERE wt.task_id = ?
    ''', (task_id,))

    task = cursor.fetchone()

    if task:
        worker_id = task['worker_id']
        worker_fio = task['worker_fio']
        task_text = task['task_text']

        # Уведомляем работника
        notification = f"""
✅ **Ваш запрос одобрен!**
──────────────
**Задание:** {task_text}
**ID запроса:** #{task_id}
**Время:** {datetime.now().strftime('%H:%M %d.%m.%Y')}
        """

        try:
            await callback.message.bot.send_message(worker_id, notification)
        except:
            pass  # Если работник заблокировал бота

    await callback.answer("✅ Задание одобрено!")
    await callback.message.edit_text(
        f"✅ Вы одобрили запрос #{task_id}",
        reply_markup=None
    )


# --- Отклонение задания от работника ---
@router.callback_query(F.data.startswith("reject_task:"))
async def reject_worker_task(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса отклонения задания"""
    user_id = callback.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await callback.answer("⛔ У вас нет прав администратора!", show_alert=True)
        return

    task_id = int(callback.data.split(":")[1])

    # Сохраняем task_id в состоянии
    await state.update_data(task_id=task_id)
    await state.set_state(AdminStates.waiting_for_comment_review)

    await callback.message.edit_text(
        f"❌ Напишите причину отклонения запроса #{task_id}:",
        reply_markup=None
    )

    await callback.answer()


@router.message(AdminStates.waiting_for_comment_review)
async def process_rejection_comment(message: types.Message, state: FSMContext):
    """Обработка комментария при отклонении задания"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    comment = message.text.strip()
    data = await state.get_data()
    task_id = data.get('task_id')
    admin_id = message.from_user.id

    if not task_id:
        await message.answer("❌ Ошибка. Попробуйте снова.")
        await state.clear()
        return

    # Обновляем статус задания с комментарием
    db.update_worker_task_status(task_id, "rejected", admin_id, comment)

    # Получаем информацию о задании
    cursor = db.conn.cursor()
    cursor.execute('''
    SELECT wt.*, u.user_id as worker_id, u.fio as worker_fio
    FROM worker_tasks wt
    JOIN users u ON wt.from_worker_id = u.user_id
    WHERE wt.task_id = ?
    ''', (task_id,))

    task = cursor.fetchone()

    if task:
        worker_id = task['worker_id']
        worker_fio = task['worker_fio']
        task_text = task['task_text']

        # Уведомляем работника
        notification = f"""
❌ **Ваш запрос отклонен**
──────────────
**Задание:** {task_text}
**ID запроса:** #{task_id}
**Причина:** {comment}
**Время:** {datetime.now().strftime('%H:%M %d.%m.%Y')}
        """

        try:
            await message.bot.send_message(worker_id, notification)
        except:
            pass  # Если работник заблокировал бота

    await message.answer(
        f"❌ Запрос #{task_id} отклонен с комментарием.",
        reply_markup=get_main_keyboard('admin')
    )

    await state.clear()


# --- Просмотр всех заданий ---
@router.message(F.text == "📊 Все задания")
async def show_all_tasks(message: types.Message):
    """Показать все задания в системе"""
    user_id = message.from_user.id

    # Проверка админа внутри функции
    if not check_admin(user_id):
        await message.answer("⛔ У вас нет прав администратора!")
        return

    print(f"🔍 ADMIN: Кнопка 'Все задания' нажата")

    cursor = db.conn.cursor()

    # Задания от администраторов
    cursor.execute('''
    SELECT at.*, 
           admin_user.fio as admin_fio,
           worker_user.fio as worker_fio
    FROM admin_tasks at
    JOIN users admin_user ON at.from_admin_id = admin_user.user_id
    JOIN users worker_user ON at.to_worker_id = worker_user.user_id
    ORDER BY at.created_at DESC
    LIMIT 20
    ''')

    admin_tasks = cursor.fetchall()

    if not admin_tasks:
        await message.answer("📭 В системе пока нет заданий.")
        return

    response = "📊 **Последние 20 заданий:**\n\n"

    for task in admin_tasks:
        task_id = task['task_id']
        task_text = task['task_text']
        status = task['status']
        created_at = task['created_at']
        admin_fio = task['admin_fio']
        worker_fio = task['worker_fio']

        status_emoji = {
            'pending': '⏳',
            'accepted': '✅',
            'completed': '✅',
            'commented': '📝'
        }.get(status, '❓')

        # Обрезаем длинный текст
        if len(task_text) > 100:
            task_text_short = task_text[:100] + "..."
        else:
            task_text_short = task_text

        response += f"{status_emoji} **Задание #{task_id}**\n"
        response += f"   От: {admin_fio} → Для: {worker_fio}\n"
        response += f"   Статус: {status}\n"
        response += f"   Текст: {task_text_short}\n"
        response += f"   Дата: {created_at}\n\n"

    await message.answer(response[:4000])  # Ограничение Telegram


# --- Тестовая кнопка для отладки ---
@router.message(F.text == "🔄 Тест")
async def test_button(message: types.Message):
    """Тестовая кнопка"""
    print(f"🔍 TEST BUTTON: Нажата user_id={message.from_user.id}")
    await message.answer("✅ Тестовая кнопка работает!")