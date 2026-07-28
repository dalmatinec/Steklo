from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_link, get_button, get_message


def _button(key: str, callback_data: str = None, url: str = None) -> InlineKeyboardButton:
    """
    Собирает кнопку из text.json: текст + цвет (style) + premium-эмодзи (icon).
    Если передан url, но ссылка ещё не настроена в link.json — используем
    callback_data-заглушку, чтобы не отправлять пустой url в Telegram.
    """
    cfg = get_button(key)
    kwargs = {
        "text": cfg.get("text", key),
        "style": cfg.get("style", "primary"),  # 'primary' синий, 'success' зелёный, 'danger' красный
    }

    icon = cfg.get("icon")
    if icon:
        kwargs["icon_custom_emoji_id"] = icon

    if url:
        kwargs["url"] = url
    elif url == "":
        kwargs["callback_data"] = f"link_{key}"
    elif callback_data:
        kwargs["callback_data"] = callback_data

    return InlineKeyboardButton(**kwargs)


def main_menu():
    """Главное меню - инлайн кнопки"""
    buttons = [
        [
            _button("chat", callback_data="link_chat"),
            _button("news", callback_data="link_news")
        ],
        [
            _button("reserve", callback_data="link_reserve")
        ],
        [
            _button("bot", url=get_link("bot")),
            _button("website", url=get_link("website"))
        ],
        [
            _button("ceo", url=get_link("ceo")),
            _button("operator", url=get_link("operator"))
        ],
        [
            _button("support", callback_data="support")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cancel_inline():
    """Кнопка отмены - инлайн"""
    text = get_message("cancel_button", "❌ Отмена")
    buttons = [[InlineKeyboardButton(text=text, callback_data="cancel_support")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_panel():
    """Админ-панель (инлайн)"""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔗 Изменить ссылки", callback_data="admin_edit_links")],
        [InlineKeyboardButton(text="👨‍💻 Изменить операторов", callback_data="admin_edit_operators")],
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
