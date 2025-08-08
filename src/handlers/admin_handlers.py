import logging

import asyncpg
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.config import ADMIN_CHAT_ID
from src.database import get_all_user_ids, get_statistics, is_admin, get_user_by_id, get_users_by_ids
from src.keyboards import (
    get_admin_menu_keyboard, get_broadcast_confirm_keyboard,
    get_broadcast_input_keyboard
)
from src.states import AdminPanel
from src.utils.validators import entities_to_html


logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, db_pool: asyncpg.Pool):
    """Обработчик команды /admin - проверка прав доступа"""
    async with db_pool.acquire() as conn:
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


@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(callback: CallbackQuery, db_pool: asyncpg.Pool):
    """Показ статистики пользователей и заявок"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return
        users_count, requests_count = await get_statistics(conn)
        await callback.message.edit_text(
            f"📊 *Статистика бота*\n\n👥 Пользователей: {users_count}\n📝 Заявок: {requests_count}",
            parse_mode="Markdown",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast(callback: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    """Запуск процесса рассылки"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return

    await callback.message.edit_text(
        "📢 *Рассылка*\n\nОтправьте сообщение для рассылки (текст, фото или фото с текстом):",
        parse_mode="Markdown",
        reply_markup=get_broadcast_input_keyboard()
    )
    await state.set_state(AdminPanel.waiting_for_broadcast_message)
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def handle_admin_users(callback: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    """Отображение списка пользователей"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return
        await show_users_page(callback.message, 1, state, conn)
        await callback.answer()


@router.callback_query(F.data == "admin_back")
async def handle_admin_back(callback: CallbackQuery):
    """Возврат в админ-меню"""
    await callback.message.edit_text(
        "🔧 *Админ-панель*\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_cancel")
async def handle_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Выход из админ-панели"""
    await callback.message.edit_text("❌ Админ-панель закрыта.", parse_mode="Markdown")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("user_info:"))
async def handle_user_info(callback: CallbackQuery, db_pool: asyncpg.Pool):
    """Показ информации о конкретном пользователе"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return
        
        user_id = int(callback.data.split(":")[1])
        user_info = await get_user_by_id(conn, user_id)
        
        if user_info:
            info_text = (
                f"👤 *Информация о пользователе*\n\n"
                f"🆔 ID: `{user_info['user_id']}`\n"
                f"📝 ФИО: {user_info['full_name']}\n"
                f"📅 Дата рождения: {user_info['birth_date']}\n"
                f"📱 Телефон: {user_info['phone_number']}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_users")]
            ])
            
            await callback.message.edit_text(
                info_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await callback.answer("❌ Пользователь не найден.", show_alert=True)


@router.callback_query(F.data.startswith("users_page:"))
async def handle_users_page(callback: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    """Обработка навигации по страницам пользователей"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return
        
        page = int(callback.data.split(":")[1])
        await show_users_page(callback.message, page, state, conn)
        await callback.answer()


@router.message(AdminPanel.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext, db_pool: asyncpg.Pool):
    """Обработка сообщения для рассылки от админа"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, message.from_user.id):
            return

    if message.message_thread_id is None:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id - 1)
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")

    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    parse_mode = "HTML" if entities else None
    if entities:
        text = entities_to_html(text, entities)

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


@router.callback_query(F.data.startswith("broadcast_"))
async def broadcast_confirm_handler(callback: CallbackQuery, state: FSMContext, db_pool: asyncpg.Pool):
    """Подтверждение или отмена рассылки"""
    async with db_pool.acquire() as conn:
        if not await is_admin(conn, callback.from_user.id):
            await callback.answer("❌ Нет доступа.", show_alert=True)
            return

        if callback.data == "broadcast_confirm":
            state_data = await state.get_data()
            broadcast_data = state_data.get("broadcast_data", {})
            success_count = 0

            try:
                user_ids = await get_all_user_ids(conn)
                for user_id in user_ids:
                    try:
                        if broadcast_data["photo"]:
                            await callback.bot.send_photo(
                                chat_id=user_id,
                                photo=broadcast_data["photo"],
                                caption=broadcast_data["text"],
                                parse_mode=broadcast_data.get("parse_mode")
                            )
                        else:
                            await callback.bot.send_message(
                                chat_id=user_id,
                                text=broadcast_data["text"],
                                parse_mode=broadcast_data.get("parse_mode")
                            )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Broadcast error to {user_id}: {e}")
                        continue

                await callback.message.edit_text(
                    f"✅ *Рассылка завершена!*\n📤 Отправлено: {success_count}/{len(user_ids)}",
                    parse_mode="Markdown",
                    reply_markup=get_admin_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Broadcast failed: {e}")
                await callback.message.edit_text(
                    "❌ Ошибка при отправке рассылки.", 
                    reply_markup=get_admin_menu_keyboard()
                )

            await state.clear()

        elif callback.data == "broadcast_cancel":
            await callback.message.edit_text("❌ Рассылка отменена.", reply_markup=get_admin_menu_keyboard())
            await state.clear()

        await callback.answer()


async def show_users_page(message: Message, page: int, state: FSMContext, conn):
    """Показ страницы пользователей с пагинацией"""
    all_user_ids = await get_all_user_ids(conn)
    total_users = len(all_user_ids)
    users_per_page = 5
    total_pages = (total_users + users_per_page - 1) // users_per_page
    page = (page - 1) % total_pages + 1  # Зацикленная пагинация

    start_idx = (page - 1) * users_per_page
    end_idx = start_idx + users_per_page
    current_users = all_user_ids[start_idx:end_idx]

    users_data = await get_users_by_ids(conn, current_users)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=user["full_name"], callback_data=f"user_info:{user['user_id']}")]
        for user in users_data
    ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="⬅️", callback_data=f"users_page:{page - 1}"),
        InlineKeyboardButton(text=f"Стр. {page}/{total_pages}", callback_data="none"),
        InlineKeyboardButton(text="➡️", callback_data=f"users_page:{page + 1}")
    ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])

    await message.edit_text(
        f"👥 *Список пользователей* (стр. {page}/{total_pages})\n\nВыберите пользователя:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.update_data(current_page=page)
