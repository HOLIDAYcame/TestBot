import logging
from typing import List, Optional, Tuple

from asyncpg import Connection


logger = logging.getLogger(__name__)


async def init_db(conn: Connection):
    """Инициализация всех таблиц в БД"""
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                full_name TEXT NOT NULL,
                birth_date DATE NOT NULL,
                phone_number TEXT NOT NULL
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                request_type TEXT NOT NULL,
                screenshot_file_id TEXT,
                options TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY
            )
        ''')
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        raise


async def register_user(conn: Connection, user_id: int, full_name: str, birth_date: str, phone_number: str):
    """Регистрация пользователя"""
    try:
        await conn.execute('''
            INSERT INTO users (user_id, full_name, birth_date, phone_number)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO NOTHING
        ''', user_id, full_name, birth_date, phone_number)
        logger.info(f"Пользователь {user_id} успешно зарегистрирован")
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя {user_id}: {e}")
        raise


async def save_request(conn: Connection, user_id: int, request_type: str, screenshot_file_id: Optional[str], options: List[str]) -> Optional[int]:
    """Сохранение заявки и возврат ID"""
    try:
        row = await conn.fetchrow('''
            INSERT INTO requests (user_id, request_type, screenshot_file_id, options)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        ''', user_id, request_type, screenshot_file_id, ", ".join(options))
        request_id = row["id"] if row else None
        logger.info(f"Заявка {request_id} успешно сохранена для пользователя {user_id}")
        return request_id
    except Exception as e:
        logger.error(f"Ошибка при сохранении заявки для пользователя {user_id}: {e}")
        raise


async def get_statistics(conn: Connection) -> Tuple[int, int]:
    """Получение статистики по пользователям и заявкам"""
    try:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        requests_count = await conn.fetchval("SELECT COUNT(*) FROM requests")
        return users_count, requests_count
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        raise


async def get_all_user_ids(conn: Connection) -> List[int]:
    """Получение списка всех user_id"""
    try:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [row["user_id"] for row in rows]
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        raise


async def is_admin(conn: Connection, user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    try:
        return await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM admins WHERE user_id = $1)", user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке прав админа для пользователя {user_id}: {e}")
        raise


async def get_user_by_id(conn: Connection, user_id: int):
    """Получение пользователя по ID"""
    try:
        return await conn.fetchrow(
            "SELECT user_id, full_name, birth_date, phone_number FROM users WHERE user_id = $1", 
            user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
        raise


async def get_users_by_ids(conn: Connection, user_ids: List[int]):
    """Получение пользователей по списку ID"""
    try:
        return await conn.fetch(
            "SELECT user_id, full_name FROM users WHERE user_id = ANY($1)", 
            user_ids
        )
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {e}")
        raise
