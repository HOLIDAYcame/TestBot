import logging
import re
from datetime import datetime

import asyncpg
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, FSInputFile, InlineKeyboardButton, 
    InlineKeyboardMarkup, Message
)

from src.config import ADMIN_CHAT_ID
from src.database import is_admin, register_user, save_request
from src.keyboards import (
    get_admin_menu_keyboard, get_cancel_keyboard, get_contacts_inline_keyboard,
    get_main_menu, get_options_inline_keyboard, get_phone_keyboard,
    get_request_type_keyboard
)
from src.states import Registration, RequestForm
from src.utils.validators import entities_to_html, is_valid_date


logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start - регистрация пользователя"""
    # Получаем пул из диспетчера
    pool = message.bot.get("db_pool")
    if not pool:
        await message.answer("Ошибка подключения к базе данных. Попробуйте позже.")
        return
    
    async with pool.acquire() as conn:
        try:
            user = await conn.fetchrow("SELECT user_id FROM users WHERE user_id=$1", message.from_user.id)
        except Exception as e:
            logger.error(f"DB error on user check: {e}")
            await message.answer("Ошибка при обращении к базе данных. Попробуйте позже.")
            return

        if user:
            await message.answer("Вы уже зарегистрированы!", reply_markup=get_main_menu())
            await state.clear()
        else:
            await message.answer("👋 Добро пожаловать! Давайте зарегистрируемся.\nПожалуйста, введите ваше ФИО:")
            await state.set_state(Registration.waiting_for_full_name)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin - проверка прав доступа"""
    pool = message.bot.get("db_pool")
    if not pool:
        await message.answer("Ошибка подключения к базе данных. Попробуйте позже.")
        return
    
    async with pool.acquire() as conn:
        try:
            if await is_admin(conn, message.from_user.id):
                await message.answer(
                    "🔧 *Админ-панель*\n\nВыберите действие:",
                    parse_mode="Markdown",
                    reply_markup=get_admin_menu_keyboard()
                )
            else:
                await message.answer("❌ У вас нет доступа к админ-панели.")
        except Exception as e:
            logger.error(f"DB error on admin check: {e}")
            await message.answer("Ошибка при проверке прав доступа. Попробуйте позже.")


@router.message(Registration.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ввода ФИО пользователя"""
    full_name = message.text.strip()
    if not full_name or len(full_name.split()) < 2:
        await message.answer("❌ Пожалуйста, введите полное ФИО (например, Иванов Иван Иванович).")
        return
    
    await state.update_data(full_name=full_name)
    await message.answer("📅 Отлично! Теперь введите дату рождения в формате ДД.ММ.ГГГГ (например, 01.01.1990):")
    await state.set_state(Registration.waiting_for_birth_date)


@router.message(Registration.waiting_for_birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    """Обработка ввода даты рождения"""
    birth_date = message.text.strip()
    if not is_valid_date(birth_date):
        await message.answer("❌ Неверный формат даты! Используйте ДД.ММ.ГГГГ (например, 01.01.1990).")
        return

    date_obj = datetime.strptime(birth_date, '%d.%m.%Y').date()
    if date_obj > datetime.now().date():
        await message.answer("❌ Дата рождения не может быть в будущем! Пожалуйста, введите корректную дату.")
        return

    await state.update_data(birth_date=birth_date)
    await message.answer("📱 Теперь поделитесь номером телефона:", reply_markup=get_phone_keyboard())
    await state.set_state(Registration.waiting_for_phone)


@router.message(Registration.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода номера телефона"""
    if not message.contact:
        await message.answer("❌ Пожалуйста, используйте кнопку для отправки номера телефона.")
        return

    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    user_data = await state.get_data()
    full_name = user_data["full_name"]
    birth_date_str = user_data["birth_date"]

    pool = message.bot.get("db_pool")
    if not pool:
        await message.answer("Ошибка подключения к базе данных. Попробуйте позже.")
        return
    
    async with pool.acquire() as conn:
        try:
            await register_user(conn, user_id, full_name, birth_date_str, phone_number)
        except Exception as e:
            logger.error(f"DB error on user registration: {e}")
            await message.answer("Ошибка при регистрации. Попробуйте позже.")
            return

        await message.answer(
            f"✅ Регистрация завершена!\nФИО: {full_name}\nДата рождения: {birth_date_str}\nТелефон: {phone_number}",
            reply_markup=get_main_menu()
        )
        await state.clear()


@router.message(F.text == "📝 Оставить заявку")
async def start_request(message: Message, state: FSMContext):
    """Начало процесса создания заявки"""
    await message.answer("Пожалуйста, выберите тип заявки:", reply_markup=get_request_type_keyboard())
    await state.set_state(RequestForm.choosing_type)


@router.message(RequestForm.choosing_type)
async def process_request_type(message: Message, state: FSMContext):
    """Обработка выбора типа заявки"""
    if message.text == "❌ Отмена":
        await message.answer("Заполнение заявки отменено.", reply_markup=get_main_menu())
        await state.clear()
        return

    if message.text not in ["🚗 Транспорт", "🏢 Офис", "📦 Доставка", "❓ Другое"]:
        await message.answer("Пожалуйста, выберите вариант из клавиатуры или нажмите ❌ Отмена.")
        return

    await state.update_data(request_type=message.text)
    await message.answer("Прикрепите скриншот, если это необходимо, или нажмите ❌ Отмена.", reply_markup=get_cancel_keyboard())
    await state.set_state(RequestForm.attaching_screenshot)


@router.message(RequestForm.attaching_screenshot)
async def process_screenshot(message: Message, state: FSMContext):
    """Обработка прикрепления скриншота"""
    if message.text == "❌ Отмена":
        await message.answer("Заполнение заявки отменено.", reply_markup=get_main_menu())
        await state.clear()
        return

    if not message.photo and message.content_type != "text":
        await message.answer("Пожалуйста, отправьте фото или нажмите ❌ Отмена.")
        return

    photo_id = message.photo[-1].file_id if message.photo else None
    await state.update_data(screenshot=photo_id)

    await message.answer("Теперь выберите, что требуется:", reply_markup=get_options_inline_keyboard())
    await state.set_state(RequestForm.choosing_options)


@router.callback_query(RequestForm.choosing_options)
async def process_options_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора опций заявки"""
    option_map = {
        "equipment": "Оборудование",
        "it": "IT-поддержка",
        "cleaning": "Уборка",
        "coffee": "Кофе"
    }

    state_data = await state.get_data()
    selected = set(state_data.get("options", []))

    if callback.data.startswith("option:"):
        await _handle_option_selection(callback, state, selected, option_map)
        return

    if callback.data == "confirm":
        await _handle_request_confirmation(callback, state, selected, option_map)


async def _handle_option_selection(callback: CallbackQuery, state: FSMContext, selected: set, option_map: dict):
    """Обработка выбора конкретной опции"""
    option = callback.data.split(":", 1)[1]
    if option in selected:
        selected.remove(option)
    else:
        selected.add(option)
    
    await state.update_data(options=list(selected))
    await callback.message.edit_reply_markup(reply_markup=get_options_inline_keyboard(selected))
    await callback.answer()


async def _handle_request_confirmation(callback: CallbackQuery, state: FSMContext, selected: set, option_map: dict):
    """Подтверждение и сохранение заявки"""
    if not selected:
        await callback.answer("Выберите хотя бы один пункт!", show_alert=True)
        return

    pool = callback.bot.get("db_pool")
    if not pool:
        await callback.message.answer("Ошибка подключения к базе данных. Попробуйте позже.", reply_markup=get_main_menu())
        await state.clear()
        await callback.answer()
        return

    async with pool.acquire() as conn:
        try:
            user_id = callback.from_user.id
            state_data = await state.get_data()
            user_info = await conn.fetchrow("SELECT full_name, phone_number FROM users WHERE user_id = $1", user_id)
            request_id = await save_request(
                conn, user_id, state_data["request_type"], state_data.get("screenshot"), list(selected)
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении заявки: {e}")
            await callback.message.answer("❌ Ошибка сохранения заявки. Попробуйте позже.", reply_markup=get_main_menu())
            await state.clear()
            await callback.answer()
            return

        await _send_request_to_admin(callback, state_data, selected, option_map, user_info, request_id)
        await callback.message.edit_reply_markup()
        await callback.message.answer("Ваша заявка отправлена! Спасибо!", reply_markup=get_main_menu())
        await state.clear()
        await callback.answer()


async def _send_request_to_admin(callback: CallbackQuery, state_data: dict, selected: set, option_map: dict, user_info: dict, request_id: int):
    """Отправка заявки администратору"""
    caption = f"Заявка №{request_id}\nОт: {user_info['full_name']} ({user_info['phone_number']})\nТип: {state_data['request_type']}\nПредметы: {', '.join([option_map.get(opt, opt) for opt in selected])}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Профиль', url=f'tg://user?id={callback.from_user.id}')]
    ])

    try:
        if state_data.get("screenshot"):
            await callback.bot.send_photo(ADMIN_CHAT_ID, state_data["screenshot"], caption=caption, reply_markup=kb)
        else:
            await callback.bot.send_message(ADMIN_CHAT_ID, caption, reply_markup=kb)
    except Exception as e:
        logger.error(f"Ошибка отправки админу: {e}")


@router.message(F.text == "📞 Контакты")
async def handle_contacts(message: Message):
    """Показ контактной информации"""
    contacts = (
        "📞 *Наши контакты*\n\n"
        "📧 *Email*: blazekartet@gmail.com\n"
        "☎️ *Телефон*: +7 (951) 891-68-71\n"
        "🏢 *Адрес*: г. Казань, ул. Товарищеская, д. 31Б\n\n"
        "👇 Наш сайт:"
    )
    await message.answer(contacts, parse_mode="Markdown", reply_markup=get_contacts_inline_keyboard())


@router.message(F.text == "ℹ️ Информация о компании")
async def handle_company_info(message: Message):
    """Показ информации о компании"""
    company_text = (
        "🌟 *О нас* 🌟\n\n"
        "Мы - *HOLIDAY Company*! 🚀\n"
        "С 2020 года мы создаём инновационные решения, которые делают жизнь проще и лучше.\n"
        "Наша миссия - объединять технологии и людей для достижения великих целей! 🌍\n\n"
        "🔹 *Что мы делаем?*\n"
        "- Разрабатываем IT-продукты\n"
        "- Помогаем бизнесу расти\n"
        "- Создаём сообщество\n\n"
        "🔹 *Почему мы?*\n"
        "- Надёжность\n"
        "- Качество\n"
        "- Команда профессионалов 💼"
    )
    try:
        await message.answer_photo(FSInputFile("images/company_logo2.jpg"), caption=company_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await message.answer(company_text, parse_mode="Markdown")
