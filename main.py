import asyncio
import logging
import os
import sys

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from firebase_admin import firestore

from database.firebase import init_firebase, get_db
from handlers import admin, client
from middlewares.admin import AdminMiddleware


# ===== API ПРИЕМНИК ЗАЯВОК С САЙТОВ КЛИЕНТОВ =====
async def handle_new_lead(request: web.Request) -> web.Response:
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    if request.method == 'OPTIONS':
        return web.Response(headers=cors_headers)

    try:
        data = await request.json()
        org_id = data.get("orgId")

        if not org_id:
            return web.json_response({"error": "orgId is required"}, status=400, headers=cors_headers)

        db = get_db()
        bot: Bot = request.app['bot']

        # 1. Сохраняем лид в CRM клиента
        lead_data = {
            "orgId": org_id,
            "name": data.get("name", "No name"),
            "phone": data.get("phone", "No phone"),
            "service": data.get("service", "Not specified"),
            "status": "New",
            "createdAt": firestore.SERVER_TIMESTAMP
        }
        db.collection("leads").add(lead_data)

        # 2. Ищем Владельца этого бизнеса в базе и отправляем ему уведомление
        # Используем ключевой аргумент filter для устранения UserWarning
        users_ref = db.collection("crm_users")
        query = users_ref.where(filter=firestore.FieldFilter("orgId", "==", org_id)).where(filter=firestore.FieldFilter("role", "==", "admin")).stream()

        for user_doc in query:
            user_data = user_doc.to_dict()
            chat_id = user_data.get("telegram_chat_id")

            if chat_id:
                text = (
                    f"🔥 <b>New Website Lead!</b>\n\n"
                    f"👤 Name: {lead_data['name']}\n"
                    f"📞 Phone: {lead_data['phone']}\n"
                    f"🛠 Service: {lead_data['service']}\n\n"
                    f"<i>Please check BWS CRM to process this lead.</i>"
                )
                try:
                    await bot.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logging.error("Failed to send notification to %s: %s", chat_id, e)

        return web.json_response({"success": True}, headers=cors_headers)

    except Exception as e:
        logging.error("API Error: %s", e)
        return web.json_response({"error": str(e)}, status=500, headers=cors_headers)


async def main() -> None:
    if os.path.exists(".env"):
        load_dotenv()

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # 1. База
    init_firebase()

    # 2. Бот
    bot = Bot(
        token=os.getenv("TELEGRAM_TOKEN"),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    dp.include_router(client.router)
    dp.include_router(admin.router)

    admin.router.message.middleware(AdminMiddleware())
    admin.router.callback_query.middleware(AdminMiddleware())

    # 3. Запуск веб-сервера aiohttp
    app = web.Application()
    app['bot'] = bot
    app.router.add_route('OPTIONS', '/api/new-lead', handle_new_lead)
    app.router.add_post('/api/new-lead', handle_new_lead)

    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"BWS API Server started on port {port}")

    # 4. Запуск бота
    logging.info("Removing old webhooks if any...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    logging.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
