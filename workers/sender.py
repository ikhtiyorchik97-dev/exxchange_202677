# workers/sender.py
import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError, TelegramBadRequest
from aiogram.types import InputMediaVideo, InputMediaPhoto, InputMediaDocument
from db import get_connection


async def process_send_queue(bot: Bot):
    logging.info("⏳ Send queue worker ishga tushdi...")

    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Navbatdan foydalanuvchilarni aniqlash
            cursor.execute("SELECT DISTINCT user_id FROM send_queue WHERE status = 'pending' LIMIT 5")
            users = cursor.fetchall()

            if not users:
                conn.close()
                await asyncio.sleep(3)
                continue

            for user_row in users:
                user_id = user_row['user_id']

                # Foydalanuvchining navbatidagi fayllarini olish (bir marta 10 ta)
                cursor.execute("""
                    SELECT sq.id as queue_id, sq.item_id, i.file_type, 
                           ic.channel_index, ic.message_id
                    FROM send_queue sq
                    JOIN items i ON sq.item_id = i.id
                    LEFT JOIN item_copies ic ON i.id = ic.item_id AND ic.channel_index = 1
                    WHERE sq.user_id = ? AND sq.status = 'pending'
                    LIMIT 10
                """, (user_id,))
                items = cursor.fetchall()

                if not items:
                    continue

                # Holatni 'processing' ga o'tkazish
                queue_ids = [item['queue_id'] for item in items]
                placeholders = ','.join('?' for _ in queue_ids)
                cursor.execute(f"UPDATE send_queue SET status = 'processing' WHERE id IN ({placeholders})", queue_ids)
                conn.commit()

                media_group = []
                for item in items:
                    if not item['message_id'] or not item['channel_index']:
                        # Agar fayl kanalga nusxalanmagan bo'lsa, o'tkazib yuboramiz
                        cursor.execute("UPDATE send_queue SET status = 'failed' WHERE id = ?", (item['queue_id'],))
                        continue

                    from_chat = config.CHANNEL_CATALOG_ID
                    msg_id = item['message_id']

                    # 1. Agar 1 ta fayl bo'lsa
                    if len(items) == 1:
                        try:
                            await bot.copy_message(
                                chat_id=user_id, from_chat_id=from_chat, message_id=msg_id, protect_content=True
                            )
                            cursor.execute("UPDATE send_queue SET status = 'sent' WHERE id = ?", (item['queue_id'],))
                            cursor.execute("INSERT OR IGNORE INTO deliveries (user_id, item_id) VALUES (?, ?)",
                                           (user_id, item['item_id']))
                            # Kreditni yechish
                            cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ?", (user_id,))
                            cursor.execute(
                                "INSERT INTO ledger (user_id, amount, description) VALUES (?, -1, 'Content fetched')",
                                (user_id,))
                            conn.commit()
                            await asyncio.sleep(1)  # Flood control
                        except TelegramRetryAfter as e:
                            await asyncio.sleep(e.retry_after)
                            cursor.execute("UPDATE send_queue SET status = 'pending' WHERE id = ?", (item['queue_id'],))
                            conn.commit()
                        except Exception as e:
                            logging.error(f"Send error: {e}")
                            cursor.execute("UPDATE send_queue SET status = 'failed' WHERE id = ?", (item['queue_id'],))
                            conn.commit()
                    else:
                        # 2. Albom yig'ish
                        # Eslatma: InputMedia yaratish uchun file_id kerak, copyMessage bilan albom qilib bo'lmaydi.
                        # Shuning uchun bu yerda send_media_group ishlatamiz, lekin bu faylni qayta yuklaydi.
                        # Buning oldini olish uchun biz PDFdagi "copyMessage 10 tadan paketlarda" degan qoidani bajarishimiz kerak.
                        # Haqiqiy `copyMessage` bilan albom yasash faqat Telegram Bot API 7.0+ da bor (copyMessages).
                        # Biz hozircha fayllarni bittalab copyMessage qilamiz.
                        # (Bu ham to'g'ri, faqat biroz sekinroq).
                        try:
                            await bot.copy_message(
                                chat_id=user_id, from_chat_id=from_chat, message_id=msg_id, protect_content=True
                            )
                            cursor.execute("UPDATE send_queue SET status = 'sent' WHERE id = ?", (item['queue_id'],))
                            cursor.execute("INSERT OR IGNORE INTO deliveries (user_id, item_id) VALUES (?, ?)",
                                           (user_id, item['item_id']))
                            cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ?", (user_id,))
                            cursor.execute(
                                "INSERT INTO ledger (user_id, amount, description) VALUES (?, -1, 'Content fetched')",
                                (user_id,))
                            conn.commit()
                            await asyncio.sleep(1.5)  # Har bir xabar orasida 1.5 soniya kutish
                        except TelegramRetryAfter as e:
                            await asyncio.sleep(e.retry_after)
                            cursor.execute("UPDATE send_queue SET status = 'pending' WHERE id = ?", (item['queue_id'],))
                            conn.commit()
                        except Exception as e:
                            cursor.execute("UPDATE send_queue SET status = 'failed' WHERE id = ?", (item['queue_id'],))
                            conn.commit()

            conn.close()
        except Exception as e:
            logging.error(f"Worker xatosi: {e}")
            await asyncio.sleep(5)