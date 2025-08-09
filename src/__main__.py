import asyncio
import logging

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat

from src.config import BOT_TOKEN, DB_CONFIG
from src.database import init_db
from src.handlers.admin_handlers import router as admin_router
from src.handlers.user_handlers import router as user_router
from src.middlewares.db_pool_middleware import DbPoolMiddleware
from src.middlewares.error_handler import ErrorHandlingMiddleware
from aiogram.utils.callback_answer import CallbackAnswerMiddleware


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():
    """Основная функция запуска бота"""
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        logger.info("Подключение к базе данных установлено")
        
        # Подключаем middleware для передачи пула
        dp.update.middleware(DbPoolMiddleware(pool))
        dp.update.middleware(ErrorHandlingMiddleware())
        dp.callback_query.middleware(CallbackAnswerMiddleware())

        dp.include_router(user_router)
        dp.include_router(admin_router)

        async with pool.acquire() as conn:
            await init_db(conn)

        # Устанавливаем команды только для обычных пользователей
        await bot.set_my_commands([
            BotCommand(command="start", description="Запустить бота")
        ])
        
        # Устанавливаем команды для админов
        async with pool.acquire() as conn:
            admin_ids = await conn.fetch("SELECT user_id FROM admins")
            for admin_row in admin_ids:
                try:
                    await bot.set_my_commands([
                        BotCommand(command="start", description="Запустить бота"),
                        BotCommand(command="admin", description="Админка")
                    ], scope=BotCommandScopeChat(chat_id=admin_row['user_id']))
                except Exception as e:
                    logger.warning(f"Не удалось установить команды для админа {admin_row['user_id']}: {e}")
        logger.info("Бот запущен и готов к работе")

        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        if 'pool' in locals():
            await pool.close()
            logger.info("Соединение с базой данных закрыто")
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    asyncio.run(main())