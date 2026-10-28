# main.py
import asyncio
import logging
import sys
import os
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

from config import config
from db import init_db, get_connection, create_or_update_user
from security import verify_telegram_init_data, verify_turnstile
from i18n import get_text

from workers.sender import process_send_queue
from workers.backup import daily_backup

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def index(request):
    return web.FileResponse('./webapp/index.html')

async def verify_captcha(request):
    try:
        data = await request.json()
        turnstile_token = data.get('token')
        init_data = data.get('initData')
        fallback_user_id = data.get('fallback_user_id')

        if not turnstile_token:
            return web.json_response({"success": False, "error": "Turnstile token missing"})

        # 1. Turnstile ni tekshirish
        if not await verify_turnstile(turnstile_token):
            return web.json_response({"success": False, "error": "Turnstile failed"})

        # 2. Foydalanuvchini aniqlash (initData yoki URL dan fallback)
        user_id = None
        if init_data:
            user_data = verify_telegram_init_data(init_data)
            if user_data and "id" in user_data:
                user_id = user_data["id"]
        
        if not user_id and fallback_user_id:
            user_id = int(fallback_user_id)

        if not user_id:
            return web.json_response({"success": False, "error": "Invalid Telegram data"})

        # 3. Tokenni saqlash
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO captcha_sessions (token, user_id, is_used) VALUES (?, ?, 1)", (turnstile_token, user_id))
        conn.commit()
        
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        lang = user['language'] if user else 'uz'
        conn.close()

        # 4. Verified qilish
        verified_until = datetime.now() + timedelta(days=config.VERIFIED_DAYS)
        create_or_update_user(user_id, state="verified", verified_until=str(verified_until))

        # 5. Xabar yuborish
        try:
            menu_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text(lang, "menu_upload"), callback_data="upload_menu")],
                [InlineKeyboardButton(text=get_text(lang, "menu_get"), callback_data="request_menu")],
                [InlineKeyboardButton(text=get_text(lang, "menu_profile"), callback_data="profile_menu")]
            ])

            temp_bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await temp_bot.send_message(
                chat_id=user_id,
                text=get_text(lang, "verified_success"),
                reply_markup=menu_kb
            )
            await temp_bot.session.close()
        except Exception as e:
            logger.error(f"Xabar yuborishda xato: {e}")

        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"CAPTCHA server xatosi: {e}")
        return web.json_response({"success": False, "error": "Server error"})

async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    from handlers.start import router as start_router
    from handlers.upload import router as upload_router
    from handlers.review import router as review_router
    from handlers.request import router as request_router
    from handlers.report import router as report_router
    from handlers.channel import router as channel_router

    dp.include_router(start_router)
    dp.include_router(upload_router)
    dp.include_router(review_router)
    dp.include_router(request_router)
    dp.include_router(report_router)
    dp.include_router(channel_router)

    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/verify-captcha', verify_captcha)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Veb-server ishga tushdi: http://0.0.0.0:{port}")

    logger.info("Bot polling va Fon ishchilari ishga tushirilmoqda...")
    await asyncio.gather(
        dp.start_polling(bot),
        process_send_queue(bot),
        daily_backup(),
        asyncio.Event().wait()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
