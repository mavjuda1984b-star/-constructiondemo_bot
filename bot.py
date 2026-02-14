# bot.py
import asyncio
import logging
import sys
import os


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import Config


from handlers import common, admin, worker


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""

    Config.validate_config()

    # Проверяем токен бота
    if not Config.BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не указан в .env файле!")
        return

    logger.info("🤖 Запуск Construction Bot...")

    # Инициализируем бота с правильными параметрами
    bot = Bot(
        token=Config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем роутеры
    dp.include_router(common.router)
    dp.include_router(worker.router)
    dp.include_router(admin.router)

    # Удаляем вебхук и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("✅ Бот запущен и готов к работе!")
    logger.info(f"👑 Администраторы: {Config.ADMIN_IDS}")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")