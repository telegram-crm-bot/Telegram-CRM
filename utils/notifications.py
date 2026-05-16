import logging

from aiogram import Bot

from database.firebase import get_db
from keyboards.client import lead_action

logger = logging.getLogger(__name__)


async def notify_new_lead(
    bot: Bot, website_id: str, lead_id: str, name: str, phone: str
) -> None:
    """
    Send a new-lead alert to the client linked to *website_id*.
    Call this from your CRM webhook or background worker.
    """
    db = get_db()
    docs = (
        db.collection("crm_users")
        .where("website_id", "==", website_id)
        .where("telegram_chat_id", "!=", None)
        .limit(1)
        .stream()
    )

    user_doc = next((doc for doc in docs), None)
    if user_doc is None:
        logger.warning("No Telegram user found for website_id %s", website_id)
        return

    chat_id = user_doc.to_dict().get("telegram_chat_id")
    text = (
        f"🆕 <b>New Lead Received!</b>\n\n"
        f"👤 Name: {name}\n"
        f"📞 Phone: {phone}\n"
        f"📌 Status: new"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=lead_action(lead_id),
        )
    except Exception as exc:
        logger.error("Failed to notify chat_id %s about lead %s: %s", chat_id, lead_id, exc)
