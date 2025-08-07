from typing import List, Optional, Tuple

from asyncpg import Connection


async def init_db(conn: Connection):
    """Инициализация всех таблиц в БД"""
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


async def register_user(conn: Connection, user_id: int, full_name: str, birth_date: str, phone_number: str):
    """Регистрация пользователя"""
    await conn.execute('''
        INSERT INTO users (user_id, full_name, birth_date, phone_number)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id) DO NOTHING
    ''', user_id, full_name, birth_date, phone_number)


async def save_request(conn: Connection, user_id: int, request_type: str, screenshot_file_id: Optional[str], options: List[str]) -> Optional[int]:
    """Сохранение заявки и возврат ID"""
    row = await conn.fetchrow('''
        INSERT INTO requests (user_id, request_type, screenshot_file_id, options)
        VALUES ($1, $2, $3, $4)
        RETURNING id
    ''', user_id, request_type, screenshot_file_id, ", ".join(options))
    return row["id"] if row else None


async def get_statistics(conn: Connection) -> Tuple[int, int]:
    """Получение статистики по пользователям и заявкам"""
    users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    requests_count = await conn.fetchval("SELECT COUNT(*) FROM requests")
    return users_count, requests_count


async def get_all_user_ids(conn: Connection) -> List[int]:
    """Получение списка всех user_id"""
    rows = await conn.fetch("SELECT user_id FROM users")
    return [row["user_id"] for row in rows]


async def is_admin(conn: Connection, user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM admins WHERE user_id = $1)", user_id
    )
