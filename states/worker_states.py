# states/worker_states.py
from aiogram.fsm.state import State, StatesGroup

class WorkerStates(StatesGroup):
    """Состояния для работника"""
    waiting_for_fio = State()           # Ожидание ввода ФИО
    waiting_for_task_text = State()     # Ожидание текста задания (для отправки админу)
    waiting_for_comment = State()       # Ожидание комментария почему не может принять
    waiting_for_task_response = State() # Ожидание ответа на задание