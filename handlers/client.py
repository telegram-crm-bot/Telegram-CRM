import logging
import os

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from database.firebase import (
    get_leads_count_by_website_id,
    get_user_by_chat_id,
    get_user_by_website_id,
    update_lead_status,
    update_user_chat_id,
)
from keyboards.client import back_to_menu, main_menu

router = Router()
logger = logging.getLogger(__name__)

CRM_WEBSITE_URL = os.getenv("CRM_WEBSITE_URL", "https://example.com")


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    """Handle deep-link auth and returning users."""
    payload = command.args  # Expected: BWS-XXXX

    if payload:
        website_id = payload.strip()
        user = get_user_by_website_id(website_id)

        if not user:
            await message.answer("❌ Invalid or expired link. User not found in CRM.")
            return

        update_user_chat_id(website_id, message.from_user.id)
        await message.answer(
            "👋 Welcome! Your CRM account is now linked.\n\nChoose an option:",
            reply_markup=main_menu(CRM_WEBSITE_URL),
        )
    else:
        user = get_user_by_chat_id(message.from_user.id)
        if user:
            await message.answer(
                "👋 Welcome back! Choose an option:",
                reply_markup=main_menu(CRM_WEBSITE_URL),
            )
        else:
            await message.answer(
                "❌ Please use the personalized link provided by your CRM to start the bot."
            )


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback_query: CallbackQuery) -> None:
    await callback_query.message.edit_text(
        "Main Menu. Choose an option:",
        reply_markup=main_menu(CRM_WEBSITE_URL),
    )
    await callback_query.answer()


@router.callback_query(F.data == "client_stats")
async def callback_stats(callback_query: CallbackQuery) -> None:
    user = get_user_by_chat_id(callback_query.from_user.id)
    if not user:
        await callback_query.answer("User not found.", show_alert=True)
        return

    website_id = user.get("website_id")
    count = get_leads_count_by_website_id(website_id)

    text = f"📊 <b>My Stats</b>\n\nTotal Leads: <b>{count}</b>"
    await callback_query.message.edit_text(text, reply_markup=back_to_menu())
    await callback_query.answer()


@router.callback_query(F.data == "client_support")
async def callback_support(callback_query: CallbackQuery) -> None:
    text = (
        "🎧 <b>Support</b>\n\n"
        "If you need help, please contact our support team at @BwsCompany_Manager"
    )
    await callback_query.message.edit_text(text, reply_markup=back_to_menu())
    await callback_query.answer()


@router.callback_query(F.data.startswith("mark_progress:"))
async def callback_mark_progress(callback_query: CallbackQuery) -> None:
    lead_id = callback_query.data.split(":", 1)[1]

    try:
        update_lead_status(lead_id, "in_progress")
        new_text = (
            f"{callback_query.message.text}\n\n"
            f"✅ Status updated to: <b>In Progress</b>"
        )
        await callback_query.message.edit_text(new_text)
        await callback_query.answer("Updated!", show_alert=False)
    except Exception as exc:
        logger.error("Error updating lead %s: %s", lead_id, exc)
        await callback_query.answer("Failed to update. Try again.", show_alert=True)
