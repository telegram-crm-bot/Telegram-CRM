from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu(website_url: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 My Stats", callback_data="client_stats"),
        InlineKeyboardButton(text="🌐 Open CRM", url=website_url),
    )
    builder.row(
        InlineKeyboardButton(text="🎧 Support", callback_data="client_support"),
    )
    return builder.as_markup()


def lead_action(lead_id: str) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Mark as In Progress", callback_data=f"mark_progress:{lead_id}"
        )
    )
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="main_menu")
    )
    return builder.as_markup()
