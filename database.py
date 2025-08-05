import asyncpg
from config import DB_CONFIG

async def init_db():
    # Создание таблицы users, если она не существует
    conn = await asyncpg.connect(**DB_CONFIG)
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            full_name TEXT NOT NULL,
            birth_date DATE NOT NULL,
            phone_number TEXT NOT NULL
        )
    ''')
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