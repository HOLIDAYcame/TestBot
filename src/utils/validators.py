import re
from datetime import datetime, date


def is_valid_date(date_str: str) -> bool:
    """Проверка корректности даты в формате ДД.ММ.ГГГГ"""
    if not date_str or not isinstance(date_str, str):
        return False
    
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
        return False
    
    try:
        parsed_date = datetime.strptime(date_str, '%d.%m.%Y').date()
        # Проверяем, что дата не в будущем и не слишком старая (например, не раньше 1900 года)
        today = date.today()
        if parsed_date > today or parsed_date.year < 1900:
            return False
        return True
    except ValueError:
        return False


def is_valid_phone(phone: str) -> bool:
    """Проверка корректности номера телефона"""
    if not phone:
        return False
    
    # Убираем все нецифровые символы
    digits_only = re.sub(r'\D', '', phone)
    
    # Проверяем, что номер содержит от 10 до 15 цифр
    return 10 <= len(digits_only) <= 15


def is_valid_full_name(full_name: str) -> bool:
    """Проверка корректности ФИО"""
    if not full_name or not isinstance(full_name, str):
        return False
    
    # Убираем лишние пробелы
    full_name = full_name.strip()
    
    # Проверяем, что ФИО содержит минимум 2 слова
    words = full_name.split()
    if len(words) < 2:
        return False
    
    # Проверяем, что каждое слово содержит только буквы, дефисы и пробелы
    for word in words:
        if not re.match(r'^[а-яёА-ЯЁa-zA-Z\-]+$', word):
            return False
    
    return True


def entities_to_html(text: str, entities: list) -> str:
    """Конвертация сущностей Telegram в HTML"""
    if not entities:
        return text
    
    sorted_entities = sorted(entities, key=lambda x: x.offset, reverse=True)
    for entity in sorted_entities:
        start = entity.offset
        end = entity.offset + entity.length
        if start >= len(text) or end > len(text):
            continue
        entity_text = text[start:end]
        replacement = {
            "bold": f"<b>{entity_text}</b>",
            "italic": f"<i>{entity_text}</i>",
            "code": f"<code>{entity_text}</code>",
            "pre": f"<pre>{entity_text}</pre>",
            "text_link": f'<a href="{entity.url}">{entity_text}</a>',
            "strikethrough": f"<del>{entity_text}</del>",
            "underline": f"<u>{entity_text}</u>",
            "spoiler": f"<tg-spoiler>{entity_text}</tg-spoiler>"
        }.get(entity.type, entity_text)
        text = text[:start] + replacement + text[end:]
    return text
