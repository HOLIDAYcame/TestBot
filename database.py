import asyncpg
from config import DB_CONFIG

async def init_db():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        # Создание таблицы users
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                full_name TEXT NOT NULL,
                birth_date DATE NOT NULL,
                phone_number TEXT NOT NULL
            )
        ''')
        # Создание таблицы requests
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
        # Создание таблицы admins
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY
            )
        ''')
    finally:
        await conn.close()

async def register_user(user_id: int, full_name: str, birth_date: str, phone_number: str):
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute('''
            INSERT INTO users (user_id, full_name, birth_date, phone_number)
            VALUES ($1, $2, $3, $4)
        ''', user_id, full_name, birth_date, phone_number)
    finally:
        await conn.close()

async def save_request(user_id: int, request_type: str, screenshot_file_id: str, options: list):
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        row = await conn.fetchrow('''
            INSERT INTO requests (user_id, request_type, screenshot_file_id, options)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        ''', user_id, request_type, screenshot_file_id, ", ".join(options))
        return row['id']
    finally:
        await conn.close()

async def get_statistics():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        requests_count = await conn.fetchval("SELECT COUNT(*) FROM requests")
        return users_count, requests_count
    finally:
        await conn.close()

async def get_all_user_ids():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        user_ids = await conn.fetch("SELECT user_id FROM users")
        return [row['user_id'] for row in user_ids]
    finally:
        await conn.close()

# функция для проверки, является ли пользователь администратором
async def is_admin(user_id: int) -> bool:
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        result = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM admins WHERE user_id = $1)", user_id)
        return result
    finally:
        await conn.close()

