from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    """Состояния для администратора"""
    waiting_for_worker_selection = State()  # Ожидание выбора работника
    waiting_for_task_text = State()         # Ожидание текста задания
    waiting_for_comment_review = State()    # Ожидание рассмотрения комментария работника