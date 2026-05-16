import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from database.firebase import init_firebase
from handlers import admin, client
from middlewares.admin import AdminMiddleware


async def main() -> None:
    # Load .env only for local dev; Railway uses dashboard env vars directly.
    if os.path.exists(".env"):
        load_dotenv()

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # 1. Connect to Firestore
    init_firebase()

    # 2. Aiogram setup
    bot = Bot(
        token=os.getenv("TELEGRAM_TOKEN"),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # 3. Routers
    dp.include_router(client.router)
    dp.include_router(admin.router)

    # 4. Middleware: lock admin commands to a single user
    admin.router.message.middleware(AdminMiddleware())
    admin.router.callback_query.middleware(AdminMiddleware())

    # 5. Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
