# handlers/common.py
from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

# АБСОЛЮТНЫЕ импорты
try:
    # Пытаемся импортировать обычным способом
    from database import Database
    from config import Config
    from keyboards import get_main_keyboard
except ImportError:
    # Если не получается, добавляем путь в sys.path
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import Database
    from config import Config
    from keyboards import get_main_keyboard

router = Router()
db = Database()


# handlers/common.py (обновленная часть)
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"

    print(f"🔍 DEBUG: /start от user_id={user_id}, username={username}")

    # Очищаем состояние
    await state.clear()

    # Проверяем, зарегистрирован ли пользователь
    user = db.get_user(user_id)

    if user:
        # Пользователь уже зарегистрирован
        fio = user[2]
        role = user[3]

        print(f"🔍 DEBUG: Пользователь найден в БД, ФИО={fio}, роль={role}")

        if role == 'admin' or Config.is_admin(user_id):
            await message.answer(
                f"👑 Добро пожаловать, администратор {fio}!",
                reply_markup=get_main_keyboard('admin')
            )
        else:
            await message.answer(
                f"👷 Добро пожаловать, {fio}!",
                reply_markup=get_main_keyboard('worker')
            )
    else:
        # Новый пользователь - просим ввести ФИО
        print(f"🔍 DEBUG: Новый пользователь, запрашиваю ФИО")

        await message.answer(
            "👋 Добро пожаловать в Construction Bot!\n\n"
            "Пожалуйста, введите ваше ФИО (полное имя):"
        )
        # Импортируем WorkerStates локально
        try:
            from states.worker_states import WorkerStates
        except ImportError:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from states.worker_states import WorkerStates

        await state.set_state(WorkerStates.waiting_for_fio)
        print(f"🔍 DEBUG: Установлено состояние: waiting_for_fio")



@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка по боту"""
    help_text = """
🤖 **Construction Bot - помощь**

**Для всех:**
/start - Начать работу с ботом
/help - Показать эту справку
/profile - Показать профиль

**Для работников:**
📋 Мои задания - Просмотр заданий от администратора
📝 Создать задание - Отправить задание на согласование
📊 Статус запросов - Мои отправленные задания

**Для администраторов:**
👥 Работники - Список всех работников
📨 Отправить задание - Назначить задание работнику
✅ Запросы от работников - Рассмотреть задания от работников
📊 Все задания - Просмотр всех заданий
    """
    await message.answer(help_text)


@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Показать профиль пользователя"""
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        user_id_db, username, fio, role, registered_at = user
        profile_text = f"""
📋 **Ваш профиль:**

👤 **ФИО:** {fio}
🆔 **ID:** {user_id_db}
👥 **Роль:** {role}
📅 **Зарегистрирован:** {registered_at}
        """
        await message.answer(profile_text)
    else:
        await message.answer("Вы еще не зарегистрированны. Нажмите /start")


@router.message(F.text == "🏠 Главное меню")
async def cmd_main_menu(message: types.Message, state: FSMContext):
    """Вернуться в главное меню"""
    await state.clear()
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        role = user[3]
        await message.answer(
            "🏠 Вы вернулись в главное меню",
            reply_markup=get_main_keyboard(role)
        )
    else:
        await cmd_start(message, state)