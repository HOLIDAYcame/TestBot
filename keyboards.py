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
        [KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="📞 Контакты")],
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