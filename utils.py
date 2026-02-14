import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_datetime(dt: Optional[str]) -> str:
    """Форматирование даты и времени"""
    if not dt:
        return "Не указано"

    try:
        # Пытаемся распарсить дату из разных форматов
        if isinstance(dt, str):
            dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        else:
            dt_obj = dt

        return dt_obj.strftime("%d.%m.%Y %H:%M")
    except Exception as e:
        logger.warning(f"Ошибка форматирования даты {dt}: {e}")
        return str(dt)


def escape_markdown(text: str) -> str:
    """Экранирование символов Markdown"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста с добавлением многоточия"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_fio(fio: str) -> tuple[bool, str]:
    """Валидация ФИО"""
    fio = fio.strip()

    if len(fio) < 2:
        return False, "❌ ФИО слишком короткое"

    if len(fio) > 100:
        return False, "❌ ФИО слишком длинное"

    # Проверяем, что есть хотя бы один пробел (имя и фамилия)
    if ' ' not in fio:
        return False, "❌ Введите полное ФИО (например: Иванов Иван)"

    return True, "✅ ФИО принято"


def get_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса"""
    emoji_map = {
        'pending': '⏳',
        'accepted': '✅',
        'completed': '✅',
        'commented': '📝',
        'approved': '✅',
        'rejected': '❌'
    }
    return emoji_map.get(status, '❓')