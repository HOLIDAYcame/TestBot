from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_phone_keyboard():
    # Клавиатура для запроса номера телефона
    button = KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_main_menu():
    # Клавиатура главного меню
    buttons = [
        [KeyboardButton(text="📝 Оставить заявку"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="ℹ️ Информация о компании")]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_contacts_inline_keyboard():
    # Инлайн-клавиатура с кнопкой-ссылкой
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Посетить наш сайт", url="https://t.me/HolidayCoChannel")]
    ])
    return keyboard

def get_request_type_keyboard():
    # Реплай-клавиатура для выбора типа заявки
    buttons = [
        [KeyboardButton(text="🚗 Транспорт"), KeyboardButton(text="🏢 Офис")],
        [KeyboardButton(text="📦 Доставка"), KeyboardButton(text="❓ Другое")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def get_cancel_keyboard():
    # Клавиатура только с кнопкой отмены
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True, one_time_keyboard=True)

def get_options_inline_keyboard(selected=None):
    # Инлайн-клавиатура с мультивыбором и подтверждением
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
        keyboard.append([InlineKeyboardButton(text=mark+text, callback_data=f"option:{callback}")])
    keyboard.append([InlineKeyboardButton(text="Подтвердить", callback_data="confirm")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_menu_keyboard():
    # Инлайн-клавиатура для админ-панели
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_confirm_keyboard():
    # Инлайн-клавиатура для подтверждения рассылки
    keyboard = [
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_input_keyboard():
    # Новая клавиатура для состояния ввода сообщения рассылки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")]
    ])
    return keyboard

def get_admin_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)