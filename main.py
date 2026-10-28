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

# O'zimizning modullar
from config import config
from db import init_db, get_connection, create_or_update_user
from security import verify_telegram_init_data, verify_turnstile
from i18n import get_text

# Fon ishchilari (Workers)
from workers.sender import process_send_queue
from workers.backup import daily_backup

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


# ==========================================
# 1. VEB SERVER QISMI (CAPTCHA va Mini App)
# ==========================================
async def index(request):
    """Mini App sahifasini (index.html) qaytaradi"""
    return web.FileResponse('./webapp/index.html')


async def verify_captcha(request):
    """Mini App dan kelgan CAPTCHA so'rovini qabul qiladi"""
    try:
        data = await request.json()
        turnstile_token = data.get('token')
        init_data = data.get('initData')

        if not turnstile_token or not init_data:
            return web.json_response({"success": False, "error": "Missing data"})

        # 1. Turnstile tokenni tekshirish
        if not await verify_turnstile(turnstile_token):
            return web.json_response({"success": False, "error": "Turnstile failed"})

        # 2. Telegram initData ni HMAC orqali tekshirish (Xavfsizlik!)
        user_data = verify_telegram_init_data(init_data)
        if not user_data or "id" not in user_data:
            return web.json_response({"success": False, "error": "Invalid Telegram data"})

        user_id = user_data["id"]

        # 3. Tokenni bir martalik qilish (captcha_sessions jadvali orqali)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO captcha_sessions (token, user_id, is_used) VALUES (?, ?, 1)",
                       (turnstile_token, user_id))
        conn.commit()

        # Foydalanuvchi tilini aniqlash
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        lang = user['language'] if user else 'uz'
        conn.close()

        # 4. Foydalanuvchini verified holatiga o'tkazish
        verified_until = datetime.now() + timedelta(days=config.VERIFIED_DAYS)
        create_or_update_user(user_id, state="verified", verified_until=str(verified_until))

        # 5. Bot orqali xabar yuborish
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


# ==========================================
# 2. ASOSIY ISHGA TUSHIRISH QISMI
# ==========================================
async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! .env faylini tekshiring.")
        return

    # Bazani ishga tushirish (schema.sql ni o'qib jadvallarni yaratadi)
    logger.info("Baza tekshirilmoqda va ishga tushirilmoqda...")
    init_db()

    # Bot va Dispatcher
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Barcha handlerlarni (routerlarni) ulash
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

    # Veb-serverni sozlash (Render va CAPTCHA uchun)
    app = web.Application()
    app.router.add_get('/', index)
    app.router.add_post('/verify-captcha', verify_captcha)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Veb-server ishga tushdi: http://0.0.0.0:{port}")

    # Bot polling, Veb-server va Fon ishchilarini parallel ishga tushirish
    logger.info("Bot polling, Veb-server va Fon ishchilari ishga tushirilmoqda...")
    await asyncio.gather(
        dp.start_polling(bot),
        process_send_queue(bot),  # Yuborish navbati (Sender Worker)
        daily_backup(),  # Kunlik zaxira (Backup Worker)
        asyncio.Event().wait()  # Dastur to'xtab qolmasligi uchun
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")