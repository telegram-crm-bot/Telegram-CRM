import logging
import os

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from database.firebase import (
    get_user_by_chat_id,
    link_user_by_uid,
    get_db
)
from keyboards.client import back_to_menu, main_menu

router = Router()
logger = logging.getLogger(__name__)

CRM_WEBSITE_URL = os.getenv("CRM_WEBSITE_URL", "https://crm.bws-company.com")


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    payload = command.args

    # Если клиент пришел по ссылке из CRM (Deep Link с UID)
    if payload:
        uid = payload.strip()
        success = link_user_by_uid(uid, str(message.from_user.id))

        if success:
            await message.answer(
                "✅ <b>Success!</b>\n\nYour BWS CRM account has been linked successfully.\nNew leads will now appear here.",
                reply_markup=main_menu(CRM_WEBSITE_URL),
            )
        else:
            await message.answer("❌ Error: User not found. Please make sure you used the link from your CRM settings.")
    
    # Обычный старт (без ссылки)
    else:
        user = get_user_by_chat_id(str(message.from_user.id))
        if user:
            await message.answer(
                "👋 Welcome back! Choose an option:",
                reply_markup=main_menu(CRM_WEBSITE_URL),
            )
        else:
            await message.answer(
                "❌ Please use the 'Connect Telegram' link from your BWS CRM settings."
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
    user = get_user_by_chat_id(str(callback_query.from_user.id))
    if not user:
        await callback_query.answer("User not found.", show_alert=True)
        return

    org_id = user.get("orgId")
    
    # Считаем лиды именно для этой организации
    db = get_db()
    docs = db.collection("leads").where("orgId", "==", org_id).stream()
    count = len(list(docs))

    text = f"📊 <b>BWS CRM Stats</b>\n\nTotal Leads: <b>{count}</b>"
    await callback_query.message.edit_text(text, reply_markup=back_to_menu())
    await callback_query.answer()


@router.callback_query(F.data == "client_support")
async def callback_support(callback_query: CallbackQuery) -> None:
    text = (
        "🎧 <b>Support</b>\n\n"
        "If you have any questions, please contact us: @BwsCompany_Manager"
    )
    await callback_query.message.edit_text(text, reply_markup=back_to_menu())
    await callback_query.answer()
