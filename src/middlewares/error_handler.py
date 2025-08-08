import logging
from typing import Any, Awaitable, Callable, Dict

import asyncpg
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import Message, TelegramObject

from src.keyboards import get_main_menu


logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)

        except asyncpg.exceptions.UniqueViolationError as e:
            logger.error(f"DB UniqueViolationError: {e}")
            if isinstance(event, Message):
                await event.answer("❌ Вы уже зарегистрированы!", reply_markup=get_main_menu())

        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"PostgreSQL error: {e}")
            if isinstance(event, Message):
                await event.answer("❌ Ошибка базы данных. Попробуйте позже.", reply_markup=get_main_menu())

        except TelegramBadRequest as e:
            logger.error(f"Telegram Bad Request: {e}")
            if isinstance(event, Message):
                await event.answer("❌ Некорректный запрос. Попробуйте снова.")

        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}")
            if isinstance(event, Message):
                await event.answer("❌ Ошибка Telegram. Попробуйте снова чуть позже.")

        except ValueError as e:
            logger.error(f"ValueError: {e}")
            if isinstance(event, Message):
                await event.answer("❌ Некорректные данные. Проверьте введенную информацию.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            if isinstance(event, Message):
                await event.answer("❌ Неизвестная ошибка. Мы уже разбираемся!", reply_markup=get_main_menu())

        return None
