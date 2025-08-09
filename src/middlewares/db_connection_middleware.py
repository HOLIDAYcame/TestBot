from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DbConnectionMiddleware(BaseMiddleware):
    """Acquires a DB connection from the pool for the lifetime of a single update.

    Injects the connection into handler data as `conn`.
    """

    def __init__(self, pool):
        super().__init__()
        self.pool = pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # prefer pool from data if already injected, otherwise use self.pool
        pool = data.get("db_pool", self.pool)
        async with pool.acquire() as conn:
            data["conn"] = conn
            return await handler(event, data)


