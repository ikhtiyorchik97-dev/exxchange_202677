import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BACKUP_BOT_TOKEN")

async def main():
    if not TOKEN:
        print("DIQQAT: BACKUP_BOT_TOKEN topilmadi! .env faylini tekshiring.")
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
    
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("Zaxira bot polling boshlandi (@BackupBot)...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
