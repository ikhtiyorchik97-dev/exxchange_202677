import asyncio
import logging
import sys
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "your_secret_key_here")

async def index(request):
    return web.FileResponse('./webapp/index.html')

async def verify_captcha(request):
    data = await request.json()
    token = data.get('token')
    user_id = data.get('user_id')
    
    if not user_id or not token:
        return web.json_response({"success": False, "error": "Missing data"})
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": TURNSTILE_SECRET_KEY,
                "response": token
            }
        ) as resp:
            result = await resp.json()
            if not result.get("success"):
                return web.json_response({"success": False, "error": "Captcha failed"})
    
    verified_until = datetime.now() + timedelta(days=30)
    from db import create_or_update_user
    create_or_update_user(user_id, state="verified", verified_until=str(verified_until))
    
    return web.json_response({"success": True})

async def main():
    if not TOKEN:
        print("DIQQAT: BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    from db import init_db
    init_db()
    
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    from handlers.start import router as start_router
    from handlers.upload import router as upload_router
    from handlers.review import router as review_router
    from handlers.request import router as request_router
    from handlers.report import router as report_router
    
    dp.include_router(start_router)
    dp.include_router(upload_router)
    dp.include_router(review_router)
    dp.include_router(request_router)
    dp.include_router(report_router)
    
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/verify-captcha', verify_captcha)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server ishga tushdi: http://0.0.0.0:{port}")
    
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("Bot polling boshlandi...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
