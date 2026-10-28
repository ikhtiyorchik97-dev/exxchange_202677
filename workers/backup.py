# workers/backup.py
import asyncio
import shutil
import os
import logging
from datetime import datetime
from config import config


async def daily_backup():
    logging.info("💾 Kunlik zaxira ishchisi ishga tushdi...")
    while True:
        try:
            # Har 24 soatda ishlaydi
            await asyncio.sleep(24 * 60 * 60)

            if os.path.exists(config.DB_NAME):
                date_str = datetime.now().strftime("%Y-%m-%d")
                backup_name = f"database_backup_{date_str}.db"
                shutil.copy2(config.DB_NAME, backup_name)
                logging.info(f"✅ Baza zaxirasi olindi: {backup_name}")

                # 7 kundan eski zaxiralarni o'chirish
                for f in os.listdir("."):
                    if f.startswith("database_backup_") and f.endswith(".db"):
                        if f != backup_name:
                            os.remove(f)
        except Exception as e:
            logging.error(f"Zaxira xatosi: {e}")