import asyncio
import logging

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from src.config import BOT_TOKEN, DB_CONFIG
from src.database import init_db
from src.handlers.admin_handlers import router as admin_router
from src.handlers.user_handlers import router as user_router
from src.middlewares.error_handler import ErrorHandlingMiddleware


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
    pool = await asyncpg.create_pool(**DB_CONFIG)
    
    # Сохраняем пул в боте для доступа из хендлеров
    bot["db_pool"] = pool
    
    dp.update.middleware(ErrorHandlingMiddleware())

    dp.include_router(user_router)
    dp.include_router(admin_router)

    async with pool.acquire() as conn:
        await init_db(conn)

    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапуск бота"),
        BotCommand(command="admin", description="Админ-панель")
    ])

    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
