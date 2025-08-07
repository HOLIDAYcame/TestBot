from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup
)


def get_phone_keyboard():
    """Клавиатура для запроса номера телефона"""
    button = KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)


def get_main_menu():
    """Клавиатура главного меню"""
    buttons = [
        [KeyboardButton(text="📝 Оставить заявку"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="ℹ️ Информация о компании")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_request_type_keyboard():
    """Клавиатура для выбора типа заявки"""
    buttons = [
        [KeyboardButton(text="🚗 Транспорт"), KeyboardButton(text="🏢 Офис")],
        [KeyboardButton(text="📦 Доставка"), KeyboardButton(text="❓ Другое")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def get_cancel_keyboard():
    """Клавиатура с одной кнопкой 'Отмена'"""
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True, one_time_keyboard=True)


def get_contacts_inline_keyboard():
    """Инлайн-клавиатура с кнопкой на сайт"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Посетить наш сайт", url="https://t.me/HolidayCoChannel")]
    ])


def get_options_inline_keyboard(selected=None):
    """Клавиатура с мультивыбором опций"""
    options = [
        ("🛠 Оборудование", "equipment"),
        ("💻 IT-поддержка", "it"),
        ("🧹 Уборка", "cleaning"),
        ("☕ Кофе", "coffee")
    ]
    if selected is None:
        selected = set()
    keyboard = []
    for text, callback in options:
        mark = "✅ " if callback in selected else ""
        keyboard.append([InlineKeyboardButton(text=mark + text, callback_data=f"option:{callback}")])
    keyboard.append([InlineKeyboardButton(text="Подтвердить", callback_data="confirm")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
