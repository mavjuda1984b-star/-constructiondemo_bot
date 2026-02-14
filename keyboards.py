from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# keyboards.py - обновленная функция get_main_keyboard
def get_main_keyboard(role: str = 'worker') -> ReplyKeyboardMarkup:
    """Главная клавиатура в зависимости от роли"""
    builder = ReplyKeyboardBuilder()

    if role == 'admin':
        builder.row(KeyboardButton(text="🔄 Тест"))  # Тестовая кнопка
        builder.row(KeyboardButton(text="👥 Работники"))
        builder.row(KeyboardButton(text="📨 Отправить задание"))
        builder.row(KeyboardButton(text="✅ Запросы от работников"))
        builder.row(KeyboardButton(text="📊 Все задания"))
        builder.row(KeyboardButton(text="🏠 Главное меню"))
    else:
        builder.row(KeyboardButton(text="📋 Мои задания"))
        builder.row(KeyboardButton(text="📝 Создать задание"))
        builder.row(KeyboardButton(text="📊 Статус запросов"))
        builder.row(KeyboardButton(text="🏠 Главное меню"))

    return builder.as_markup(resize_keyboard=True)


def get_workers_keyboard(workers: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора работника"""
    builder = InlineKeyboardBuilder()

    for worker in workers:
        worker_id, fio = worker
        builder.button(text=f"👷 {fio}", callback_data=f"select_worker:{worker_id}")

    builder.adjust(1)
    return builder.as_markup()


def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с заданием"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ ПРИНЯТЬ", callback_data=f"accept_task:{task_id}")
    builder.button(text="📝 КОММЕНТАРИЙ", callback_data=f"comment_task:{task_id}")

    builder.adjust(1)
    return builder.as_markup()


def get_worker_task_review_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для рассмотрения задания от работника"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Одобрить", callback_data=f"approve_task:{task_id}")
    builder.button(text="❌ Отклонить", callback_data=f"reject_task:{task_id}")

    builder.adjust(2)
    return builder.as_markup()


def get_back_to_menu_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для возврата в меню"""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏠 Главное меню")
    return builder.as_markup(resize_keyboard=True)