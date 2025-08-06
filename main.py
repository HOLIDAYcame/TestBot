import re
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile, CallbackQuery, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton  
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.exceptions import TelegramAPIError
import asyncpg
from config import BOT_TOKEN
from database import init_db, register_user, save_request, get_statistics, get_all_user_ids, is_admin
from keyboards import get_phone_keyboard, get_main_menu, get_contacts_inline_keyboard, get_request_type_keyboard, get_cancel_keyboard, get_admin_menu_keyboard, get_broadcast_confirm_keyboard, get_broadcast_input_keyboard
from states import Registration, RequestForm, AdminPanel
import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

def is_valid_date(date_str: str) -> bool:
    pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(pattern, date_str):
        return False
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False

def entities_to_html(text: str, entities: list) -> str:
    if not entities:
        return text
    sorted_entities = sorted(entities, key=lambda x: x.offset, reverse=True)
    result = text
    for entity in sorted_entities:
        start = entity.offset
        end = entity.offset + entity.length
        if start >= len(result) or end > len(result):
            continue
        entity_text = result[start:end]
        if entity.type == "bold":
            replacement = f"<b>{entity_text}</b>"
        elif entity.type == "italic":
            replacement = f"<i>{entity_text}</i>"
        elif entity.type == "code":
            replacement = f"<code>{entity_text}</code>"
        elif entity.type == "pre":
            replacement = f"<pre>{entity_text}</pre>"
        elif entity.type == "text_link":
            replacement = f'<a href="{entity.url}">{entity_text}</a>'
        elif entity.type == "strikethrough":
            replacement = f"<del>{entity_text}</del>"
        elif entity.type == "underline":
            replacement = f"<u>{entity_text}</u>"
        elif entity.type == "spoiler":
            replacement = f"<tg-spoiler>{entity_text}</tg-spoiler>"
        else:
            continue
        result = result[:start] + replacement + result[end:]
    return result

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    import asyncpg
    user_id = message.from_user.id
    try:
        conn = await asyncpg.connect(**config.DB_CONFIG)
        user = await conn.fetchrow("SELECT user_id FROM users WHERE user_id=$1", user_id)
        await conn.close()
    except Exception as e:
        logger.error(f"DB error on user check: {e}")
        await message.answer("Ошибка при обращении к базе данных. Попробуйте позже.")
        return
    if user:
        await message.answer("Вы уже зарегистрированы!", reply_markup=get_main_menu())
        await state.clear()
    else:
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
    try:
        date_obj = datetime.strptime(birth_date, '%d.%m.%Y').date()
        if date_obj > datetime.now().date():
            await message.answer("❌ Дата рождения не может быть в будущем! Пожалуйста, введите корректную дату.")
            return
    except Exception:
        await message.answer("❌ Ошибка обработки даты. Попробуйте снова.")
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
        birth_date = datetime.strptime(birth_date_str, '%d.%m.%Y').date()
    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        await message.answer("❌ Ошибка обработки даты рождения. Попробуйте начать заново с /start.")
        await state.clear()
        return
    user_id = message.from_user.id
    try:
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
        await message.answer(
            "❌ Вы уже зарегистрированы! Выберите действие в меню:",
            reply_markup=get_main_menu()
        )
        await state.clear()

@dp.message(lambda message: message.text == "📝 Оставить заявку")
async def start_request(message: Message, state: FSMContext):
    await message.answer(
        "Пожалуйста, выберите тип заявки:",
        reply_markup=get_request_type_keyboard()
    )
    await state.set_state(RequestForm.choosing_type)

@dp.message(RequestForm.choosing_type)
async def process_request_type(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Заполнение заявки отменено.", reply_markup=get_main_menu())
        await state.clear()
        return
    if message.text not in ["🚗 Транспорт", "🏢 Офис", "📦 Доставка", "❓ Другое"]:
        await message.answer("Пожалуйста, выберите вариант из клавиатуры или нажмите ❌ Отмена.", reply_markup=get_request_type_keyboard())
        return
    await state.update_data(request_type=message.text)
    await message.answer(
        "Прикрепите скриншот, если это необходимо, или нажмите ❌ Отмена.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(RequestForm.attaching_screenshot)

@dp.message(RequestForm.attaching_screenshot)
async def process_screenshot(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await message.answer("Заполнение заявки отменено.", reply_markup=get_main_menu())
        await state.clear()
        return
    if not message.photo and message.content_type != 'text':
        await message.answer("Пожалуйста, отправьте фото или нажмите ❌ Отмена.", reply_markup=get_cancel_keyboard())
        return
    if message.photo:
        photo_id = message.photo[-1].file_id
        await state.update_data(screenshot=photo_id)
        await message.answer("Фото получено! Теперь выберите, что требуется:", reply_markup=None)
    else:
        await state.update_data(screenshot=None)
        await message.answer("Фото не прикреплено. Теперь выберите, что требуется:", reply_markup=None)
    from keyboards import get_options_inline_keyboard
    await message.answer(
        "Выберите один или несколько пунктов (можно нажимать несколько раз, выбранные отмечаются галочкой):",
        reply_markup=get_options_inline_keyboard()
    )
    await state.set_state(RequestForm.choosing_options)

@dp.callback_query(RequestForm.choosing_options)
async def process_options_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = set(data.get("options", []))
    option_map = {
        "equipment": "Оборудование",
        "it": "IT-поддержка",
        "cleaning": "Уборка",
        "coffee": "Кофе"
    }
    if callback.data.startswith("option:"):
        option = callback.data.split(":", 1)[1]
        if option in selected:
            selected.remove(option)
        else:
            selected.add(option)
        await state.update_data(options=list(selected))
        from keyboards import get_options_inline_keyboard
        await callback.message.edit_reply_markup(reply_markup=get_options_inline_keyboard(selected))
        await callback.answer()
    elif callback.data == "confirm":
        data = await state.get_data()
        selected = set(data.get("options", []))
        if not selected:
            await callback.answer("Выберите хотя бы один пункт!", show_alert=True)
            return
        user_id = callback.from_user.id
        request_type = data.get("request_type")
        screenshot = data.get("screenshot")
        options = list(selected)
        import asyncpg
        try:
            conn = await asyncpg.connect(**config.DB_CONFIG)
            user = await conn.fetchrow("SELECT full_name, phone_number FROM users WHERE user_id=$1", user_id)
            await conn.close()
        except Exception as e:
            logger.error(f"DB error on user fetch: {e}")
            await callback.message.answer("Ошибка при получении данных пользователя. Попробуйте позже.", reply_markup=get_main_menu())
            await state.clear()
            await callback.answer()
            return
        full_name = user["full_name"] if user else "-"
        phone = user["phone_number"] if user else "-"
        try:
            request_id = await save_request(user_id, request_type, screenshot, options)
        except Exception as e:
            logger.error(f"DB error on request save: {e}")
            await callback.message.answer("Ошибка при сохранении заявки. Попробуйте позже.", reply_markup=get_main_menu())
            await state.clear()
            await callback.answer()
            return
        ADMIN_CHAT_ID = -1002755127121
        rus_options = [option_map.get(opt, opt) for opt in options]
        text = f"Заявка №{request_id}\nОт: {full_name} ({phone})\nТип: {request_type}\nПредметы: {', '.join(rus_options) if rus_options else '-'}"
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Профиль', url=f'tg://user?id={user_id}')
        ]])
        try:
            if screenshot:
                await bot.send_photo(ADMIN_CHAT_ID, photo=screenshot, caption=text, reply_markup=kb)
            else:
                await bot.send_message(ADMIN_CHAT_ID, text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения админам с кнопкой: {e}")
            try:
                if screenshot:
                    await bot.send_photo(ADMIN_CHAT_ID, photo=screenshot, caption=text)
                else:
                    await bot.send_message(ADMIN_CHAT_ID, text)
            except Exception as e2:
                logger.error(f"Ошибка отправки сообщения админам без кнопки: {e2}")
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.message.answer("Ваша заявка отправлена! Спасибо!", reply_markup=get_main_menu())
        await state.clear()
        await callback.answer()
    else:
        await callback.answer("Неизвестное действие.", show_alert=True)

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
    except Exception as e:
        logger.error(f"Image file not found or error: {e}")
        await message.answer(company_text, parse_mode="Markdown")

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    await message.answer(
        "🔧 *Админ-панель*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("admin_"))
async def admin_callback_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    if callback.data == "admin_stats":
        users_count, requests_count = await get_statistics()
        stats_text = f"📊 *Статистика бота*\n\n👥 Пользователей: {users_count}\n📝 Заявок: {requests_count}"
        await callback.message.edit_text(stats_text, parse_mode="Markdown", reply_markup=get_admin_menu_keyboard())
    
    elif callback.data == "admin_broadcast":
        await callback.message.edit_text(
            "📢 *Рассылка*\n\nОтправьте сообщение для рассылки (текст, фото или фото с текстом):",
            parse_mode="Markdown",
            reply_markup=get_broadcast_input_keyboard()
        )
        await state.set_state(AdminPanel.waiting_for_broadcast_message)
    
    elif callback.data == "admin_users":
        page = 1  
        await show_users_page(callback.message, page, state)
    
    elif callback.data == "admin_back":
        await callback.message.edit_text(
            "🔧 *Админ-панель*\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )
    
    elif callback.data == "admin_cancel":
        await callback.message.edit_text(
            "❌ Админ-панель закрыта.",
            parse_mode="Markdown"
        )
        await state.clear()
    
    await callback.answer()

@dp.message(AdminPanel.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return
    
    if message.message_thread_id is None:  
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")
    
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    
    if entities:
        text = entities_to_html(text, entities)
        parse_mode = "HTML"
    else:
        parse_mode = None
    
    broadcast_data = {
        "text": text,
        "photo": message.photo[-1].file_id if message.photo else None,
        "parse_mode": parse_mode
    }
    await state.update_data(broadcast_data=broadcast_data)
    
    preview_text = f"📢 *Предварительный просмотр рассылки:*\n\n"
    if broadcast_data["photo"]:
        preview_text += "📷 *Фото:* Да\n"
    preview_text += f"📝 *Текст:* {broadcast_data['text'][:100]}{'...' if len(broadcast_data['text']) > 100 else ''}"
    
    if broadcast_data["photo"]:
        await message.answer_photo(
            photo=broadcast_data["photo"],
            caption=preview_text,
            parse_mode="Markdown",
            reply_markup=get_broadcast_confirm_keyboard()
        )
    else:
        await message.answer(
            preview_text,
            parse_mode="Markdown",
            reply_markup=get_broadcast_confirm_keyboard()
        )
    await state.set_state(AdminPanel.confirming_broadcast)

@dp.callback_query(lambda c: c.data.startswith("broadcast_"))
async def broadcast_confirm_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    if callback.data == "broadcast_confirm":
        data = await state.get_data()
        broadcast_data = data.get("broadcast_data", {})
        
        try:
            user_ids = await get_all_user_ids()
            success_count = 0
            
            for user_id in user_ids:
                try:
                    if broadcast_data["photo"]:
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=broadcast_data["photo"],
                            caption=broadcast_data["text"],
                            parse_mode=broadcast_data.get("parse_mode")
                        )
                    else:
                        await bot.send_message(
                            chat_id=user_id,
                            text=broadcast_data["text"],
                            parse_mode=broadcast_data.get("parse_mode")
                        )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {user_id}: {e}")
                    continue
            
            await callback.message.edit_text(
                f"✅ *Рассылка завершена!*\n\n📤 Отправлено: {success_count}/{len(user_ids)} пользователей",
                parse_mode="Markdown",
                reply_markup=get_admin_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при отправке рассылки.",
                reply_markup=get_admin_menu_keyboard()
            )
        await state.clear()
    
    elif callback.data == "broadcast_cancel":
        await callback.message.edit_text(
            "❌ Рассылка отменена.",
            reply_markup=get_admin_menu_keyboard()
        )
        await state.clear()
    
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("users_page:") or c.data.startswith("user_info:"))
async def user_pagination_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    if callback.data.startswith("users_page:"):
        page = int(callback.data.split(":")[1])
        await show_users_page(callback.message, page, state)
    
    elif callback.data.startswith("user_info:"):
        user_id = int(callback.data.split(":")[1])
        conn = await asyncpg.connect(**config.DB_CONFIG)
        try:
            user = await conn.fetchrow("SELECT user_id, full_name, birth_date, phone_number FROM users WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        if user:
            user_info = (
                f"ℹ️ *Информация о пользователе*\n\n"
                f"👤 Имя: {user['full_name']}\n"
                f"📅 Дата рождения: {user['birth_date'].strftime('%d.%m.%Y')}\n"
                f"📱 Телефон: {user['phone_number']}"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="users_back")]
            ])
            await callback.message.edit_text(user_info, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await callback.message.edit_text("❌ Пользователь не найден.", reply_markup=get_admin_menu_keyboard())
    
    await callback.answer()

@dp.callback_query(lambda c: c.data == "users_back")
async def user_back_handler(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели.", show_alert=True)
        return
    
    data = await state.get_data()  
    page = data.get("current_page", 1)  
    await show_users_page(callback.message, page, state)
    await callback.answer()


async def show_users_page(message: types.Message, page: int, state: FSMContext):
    all_user_ids = await get_all_user_ids()
    total_users = len(all_user_ids)
    users_per_page = 5
    total_pages = (total_users + users_per_page - 1) // users_per_page
    if page < 1:
        page = total_pages
    elif page > total_pages:
        page = 1
    
    start_idx = (page - 1) * users_per_page
    end_idx = start_idx + users_per_page
    current_users = all_user_ids[start_idx:end_idx]
    
    conn = await asyncpg.connect(**config.DB_CONFIG)
    try:
        users_data = await conn.fetch("SELECT user_id, full_name, birth_date, phone_number FROM users WHERE user_id = ANY($1)", current_users)
    finally:
        await conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for user in users_data:
        user_id = user["user_id"]
        full_name = user["full_name"]
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=full_name, callback_data=f"user_info:{user_id}")])
    
    # Кнопки пагинации
    pagination = [
        InlineKeyboardButton(text="⬅️", callback_data=f"users_page:{page - 1}" if page > 1 else f"users_page:{total_pages}"),
        InlineKeyboardButton(text=f"Стр. {page}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=f"users_page:{page + 1}" if page < total_pages else f"users_page:1")
    ]
    keyboard.inline_keyboard.append(pagination)
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    
    await message.edit_text(
        f"👥 *Список пользователей* (Стр. {page}/{total_pages})\n\nВыберите пользователя:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.update_data(current_page=page)

async def main():
    dp.update.middleware(ErrorHandlingMiddleware())
    await init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапустить бота"),
        BotCommand(command="admin", description="Админ-панель"),
    ])
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

