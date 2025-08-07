import re
from datetime import datetime


def is_valid_date(date_str: str) -> bool:
    """Проверка корректности даты в формате ДД.ММ.ГГГГ"""
    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
        return False
    try:
        datetime.strptime(date_str, '%d.%m.%Y')
        return True
    except ValueError:
        return False


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
