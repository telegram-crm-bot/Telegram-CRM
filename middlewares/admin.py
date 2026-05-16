import os
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))


class AdminMiddleware(BaseMiddleware):
    """Restricts all handlers on the mounted router to the single ADMIN_CHAT_ID."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and user.id == ADMIN_CHAT_ID:
            return await handler(event, data)
        # Silently drop non-admin interactions on this router
        return None
