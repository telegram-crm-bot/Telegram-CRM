import asyncio
import logging

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from database.firebase import check_connection, get_all_registered_chat_ids, get_db

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    db = get_db()
    users = db.collection("crm_users").where("telegram_chat_id", "!=", None).stream()
    total_users = len(list(users))
    db_status = check_connection()

    text = (
        f"🛡 <b>Admin Dashboard</b>\n\n"
        f"👥 Total Registered Users: <b>{total_users}</b>\n"
        f"🗄 Database Status: <b>{db_status}</b>"
    )
    await message.answer(text)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: <code>/broadcast &lt;text&gt;</code>")
        return

    text = command.args
    chat_ids = get_all_registered_chat_ids()

    if not chat_ids:
        await message.answer("No registered users found.")
        return

    sent = 0
    failed = 0
    status_msg = await message.answer(f"Broadcasting to {len(chat_ids)} users…")

    for chat_id in chat_ids:
        try:
            await message.bot.send_message(
                chat_id=chat_id,
                text=f"📢 <b>Announcement</b>\n\n{text}",
            )
            sent += 1
            await asyncio.sleep(0.05)  # Gentle rate-limiting
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await message.bot.send_message(
                    chat_id=chat_id,
                    text=f"📢 <b>Announcement</b>\n\n{text}",
                )
                sent += 1
            except Exception as retry_exc:
                logger.error("Retry failed for %s: %s", chat_id, retry_exc)
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            logger.warning("Cannot send to %s: %s", chat_id, exc)
            failed += 1
        except Exception as exc:
            logger.error("Unexpected error sending to %s: %s", chat_id, exc)
            failed += 1

    await status_msg.edit_text(
        f"✅ Broadcast complete.\n\nSent: <b>{sent}</b>\nFailed: <b>{failed}</b>"
    )
