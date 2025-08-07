import asyncio
import asyncpg
from config import DB_CONFIG

async def fix_admins_table():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        await conn.execute('DROP TABLE IF EXISTS admins')
        await conn.execute('''
            CREATE TABLE admins (
                user_id BIGINT PRIMARY KEY
            )
        ''')

        """ Добавляем начальных администраторов"""
        
        admin_ids = [6942471653, 2032621151, 789420601]
        for admin_id in admin_ids:
            await conn.execute('''
                INSERT INTO admins (user_id)
                VALUES ($1)
                ON CONFLICT (user_id) DO NOTHING
            ''', admin_id)
        print("Таблица admins создана и администраторы добавлены.")
    finally:
        await conn.close()

asyncio.run(fix_admins_table())