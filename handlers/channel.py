# handlers/channel.py
from aiogram import Router, F
from aiogram.types import Message
from db import get_connection
from config import config
import logging

router = Router()


# Bot qaysi kanalga qo'shilsa yoki u yerga post tashlansa ishlaydi
@router.channel_post()
async def handle_channel_post(message: Message):
    # Faqat katalog kanaliga tushgan fayllarni bazaga yozamiz
    if message.chat.id != config.CHANNEL_CATALOG_ID:
        return

    file_type = None
    file_id = None
    file_unique_id = None
    duration = 0
    file_size = 0

    if message.video:
        file_type = 'video'
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        duration = message.video.duration or 0
        file_size = message.video.file_size or 0
    elif message.photo:
        file_type = 'photo'
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
        file_size = message.photo[-1].file_size or 0
    elif message.document:
        file_type = 'document'
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
        file_size = message.document.file_size or 0
    else:
        return  # Boshqa turdagi xabarlar

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Bazaga faylni yozish (Admin tomonidan yuklangan deb hisoblaymiz, user_id=0)
        cursor.execute("""
            INSERT INTO items (user_id, file_type, file_id, file_unique_id, duration, file_size, status)
            VALUES (0, ?, ?, ?, ?, ?, 'approved')
        """, (file_type, file_id, file_unique_id, duration, file_size))

        item_id = cursor.lastrowid

        # 2. Nusxasini item_copies ga yozish (1-kanal)
        cursor.execute("INSERT INTO item_copies (item_id, channel_index, message_id) VALUES (?, 1, ?)",
                       (item_id, message.message_id))
        conn.commit()
        logging.info(f"Kanalxonadan yangi fayl bazaga yozildi. ID: {item_id}")
    except Exception as e:
        # Dublikat bo'lsa xato bermaydi
        logging.debug(f"Kanalxona fayli bazada mavjud: {e}")
    finally:
        conn.close()