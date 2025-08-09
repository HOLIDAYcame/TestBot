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

_admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(_admin_chat_id_raw) if _admin_chat_id_raw else None

# Перечень админов через запятую (если задан, используется вместо проверки в БД)
_admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
if _admin_ids_raw:
    try:
        ADMIN_IDS = {int(x) for x in _admin_ids_raw.replace(" ", "").split(",") if x}
    except ValueError:
        raise ValueError("ADMIN_IDS должен содержать список целых чисел, разделённых запятыми")
else:
    ADMIN_IDS = set()

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
