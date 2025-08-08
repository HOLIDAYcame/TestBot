import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# Проверяем обязательные параметры БД
if not all([DB_CONFIG["database"], DB_CONFIG["user"], DB_CONFIG["password"]]):
    raise ValueError("Не все обязательные параметры БД указаны в переменных окружения")

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не найден в переменных окружения")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# Текстовые константы
COMPANY_INFO = """🌟 *О нас* 🌟

Мы - *HOLIDAY Company*! 🚀
С 2020 года мы создаём инновационные решения, которые делают жизнь проще и лучше.
Наша миссия - объединять технологии и людей для достижения великих целей! 🌍

🔹 *Что мы делаем?*
- Разрабатываем IT-продукты
- Помогаем бизнесу расти
- Создаём сообщество

🔹 *Почему мы?*
- Надёжность
- Качество
- Команда профессионалов 💼"""

CONTACTS_INFO = """📞 *Наши контакты*

📧 *Email*: blazekartet@gmail.com
☎️ *Телефон*: +7 (951) 891-68-71
🏢 *Адрес*: г. Казань, ул. Товарищеская, д. 31Б

👇 Наш сайт:"""
