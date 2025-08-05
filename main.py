import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
import asyncpg
from config import BOT_TOKEN
from database import init_db, register_user
from keyboards import get_phone_keyboard, get_main_menu, get_contacts_inline_keyboard
from states import Registration

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),  # Сохраняем логи в файл
        logging.StreamHandler()  # Выводим логи в консоль
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Middleware для обработки ошибок
class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except asyncpg.exceptions.UniqueViolationError as e:
            logger.error(f"Database error (UniqueViolation): {e}")
            if isinstance(event, Message):
                await event.answer(
                    "❌ Ошибка: Вы уже зарегистрированы! Попробуйте другое действие.",
                    reply_markup=get_main_menu()
                )
        except asyncpg.exceptions.PostgresError as e:
            logger.error(f"Database error: {e}")
            if isinstance(event, Message):
                await event.answer(
                    "❌ Ошибка базы данных. Пожалуйста, попробуйте позже.",
                    reply_markup=get_main_menu()
                )
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}")
            if isinstance(event, Message):
                await event.answer(
                    "❌ Ошибка Telegram. Возможно, слишком много запросов. Попробуйте снова через минуту."
                )
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            if isinstance(event, Message):
                await event.answer(
                    "❌ Произошла неизвестная ошибка. Мы уже работаем над её исправлением! 😊",
                    reply_markup=get_main_menu()
                )
        return

# Проверка формата даты ДД.ММ.ГГГГ
def is_valid_date(date_str: str) -> bool:
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "👋 Добро пожаловать! Давайте зарегистрируемся.\n"
        "Пожалуйста, введите ваше ФИО:"
    )
    await state.set_state(Registration.waiting_for_full_name)

@dp.message(Registration.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if not full_name or len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введите полное ФИО (например, Иванов Иван Иванович).")
        return
    await state.update_data(full_name=full_name)
    await message.answer(
        "📅 Отлично! Теперь введите дату рождения в формате ДД.ММ.ГГГГ (например, 01.01.1990):"
    )
    await state.set_state(Registration.waiting_for_birth_date)

@dp.message(Registration.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    birth_date = message.text.strip()
    if not is_valid_date(birth_date):
        await message.answer("❌ Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 01.01.1990).")
        return
    await state.update_data(birth_date=birth_date)
    await message.answer(
        "📱 Теперь поделитесь номером телефона:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(Registration.waiting_for_phone)

@dp.message(Registration.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    if not message.contact:
        await message.answer("❌ Пожалуйста, используйте кнопку для отправки номера телефона.")
        return

    phone_number = message.contact.phone_number
    user_data = await state.get_data()
    full_name = user_data["full_name"]
    birth_date_str = user_data["birth_date"]
    
    try:
        # Преобразуем строку birth_date в объект datetime.date
        birth_date = datetime.strptime(birth_date_str, '%d.%m.%Y').date()
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        await message.answer("❌ Ошибка обработки даты рождения. Попробуйте начать заново с /start.")
        await state.clear()
        return
    
    user_id = message.from_user.id

    try:
        # Сохранение в базу данных
        await register_user(user_id, full_name, birth_date, phone_number)
        await message.answer(
            "✅ Регистрация завершена!\n"
            f"ФИО: {full_name}\n"
            f"Дата рождения: {birth_date_str}\n"
            f"Номер телефона: {phone_number}\n\n"
            "Выберите действие в меню ниже:",
            reply_markup=get_main_menu()
        )
        await state.clear()
    except asyncpg.exceptions.UniqueViolationError:
        # Уже обработано в middleware, но оставим для явной логики
        await message.answer(
            "❌ Вы уже зарегистрированы! Выберите действие в меню:",
            reply_markup=get_main_menu()
        )
        await state.clear()

# Обработчики для кнопок меню с использованием лямбда-функций
@dp.message(lambda message: message.text == "📝 Оставить заявку")
async def handle_request(message: Message):
    await message.answer(
        "📝 *Оставить заявку* 📝\n\n"
        "Этот раздел находится в разработке! 🔧\n"
        "Скоро вы сможете оставить заявку прямо здесь. Следите за обновлениями! 😊",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "📞 Контакты")
async def handle_contacts(message: Message):
    contacts_text = (
        "📞 *Наши контакты* 📞\n\n"
        "Свяжитесь с нами удобным способом:\n"
        "📧 *Email*: blazekartet@gmail.com\n"
        "☎️ *Телефон*: +7 (951) 891-68-71\n"
        "🏢 *Адрес*: г. Казань, ул. Товарищеская, д. 31Б\n\n"
        "Посетите наш сайт для подробной информации! 👇"
    )
    await message.answer(
        contacts_text,
        parse_mode="Markdown",
        reply_markup=get_contacts_inline_keyboard()
    )

@dp.message(lambda message: message.text == "ℹ️ Информация о компании")
async def handle_company_info(message: Message):
    company_text = (
        "🌟 *О нас* 🌟\n\n"
        "Мы - *HOLIDAY Company*! 🚀\n"
        "С 2020 года мы создаём инновационные решения, которые делают жизнь проще и лучше. "
        "Наша миссия - объединять технологии и людей для достижения великих целей! 🌍\n\n"
        "🔹 *Что мы делаем?*\n"
        "- Разрабатываем передовые IT-продукты.\n"
        "- Помогаем бизнесам расти с помощью технологий.\n"
        "- Создаём сообщество единомышленников!\n\n"
        "🔹 *Почему выбирают нас?*\n"
        "- Надёжность и качество.\n"
        "- Индивидуальный подход.\n"
        "- Команда профессионалов! 💼\n\n"
        "Будем рады сотрудничеству! 😊"
    )
    
    try:
        await message.answer_photo(
            photo=FSInputFile("images/company_logo2.jpg"),
            caption=company_text,
            parse_mode="Markdown"
        )
    except FileNotFoundError as e:
        logger.error(f"Image file not found: {e}")
        await message.answer(
            "❌ Ошибка: не удалось загрузить изображение. Вот информация о компании:\n\n" + company_text,
            parse_mode="Markdown"
        )

async def main():
    # Регистрируем middleware
    dp.update.middleware(ErrorHandlingMiddleware())
    await init_db()  # Инициализация базы данных
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())