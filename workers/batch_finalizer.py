# workers/batch_finalizer.py
import asyncio
import os
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_connection
from config import config


async def finalize_batch(batch_id: int, bot: Bot):
    """
    15 soniya o'tgach yoki foydalanuvchi "Tugatdim" bosganda paketni yakunlaydi.
    Admin guruhiga tekshirish uchun yuboradi.
    """
    await asyncio.sleep(15)  # 15 soniya kutish

    conn = get_connection()
    cursor = conn.cursor()

    # Paket holatini tekshirish
    cursor.execute("SELECT user_id, status FROM batches WHERE id = ?", (batch_id,))
    batch = cursor.fetchone()

    if not batch or batch['status'] != 'collecting':
        conn.close()
        return

    user_id = batch['user_id']

    # Paketdagi fayllarni olish
    cursor.execute("SELECT id, file_type FROM items WHERE batch_id = ? AND status = 'pending'", (batch_id,))
    items = cursor.fetchall()

    if not items:
        cursor.execute("UPDATE batches SET status = 'rejected' WHERE id = ?", (batch_id,))
        conn.commit()
        conn.close()
        return

    # Holatni pending ga o'zgartirish
    cursor.execute("UPDATE batches SET status = 'pending' WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()

    # Admin guruhiga xabar yuborish
    if not config.ADMIN_GROUP_ID:
        return

    total_files = len(items)
    file_types = [item['file_type'] for item in items]

    # Tugmalar
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_batch_{batch_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_batch_{batch_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Ban qilish", callback_data=f"ban_user_{user_id}")
        ]
    ])

    text = (
        f"📥 <b>Yangi paket keldi!</b>\n\n"
        f"👤 Foydalanuvchi ID: <code>{user_id}</code>\n"
        f"📦 Fayllar soni: {total_files} ta\n"
        f"📄 Turlari: {', '.join(set(file_types))}\n\n"
        f"<i>Tasdiqlansa, barcha fayllar kanallarga nusxalanadi va foydalanuvchiga kredit beriladi.</i>"
    )

    try:
        # PDF 5-bo'lim: "admin guruhiga namuna yuboriladi". Hozircha bitta xabar yuboramiz
        msg = await bot.send_message(config.ADMIN_GROUP_ID, text, reply_markup=kb, parse_mode="HTML")

        # Xabar ID sini bazaga saqlash (keyinroq tahrirlash uchun)
        conn = get_connection()
        conn.execute("UPDATE batches SET admin_msg_id = ? WHERE id = ?", (msg.message_id, batch_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Admin guruhiga yuborishda xato: {e}")

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(user_id,
                               "⏳ Fayllaringiz qabul qilindi. Adminlar tekshiruviga yuborildi. Iltimos, kuting.")
    except:
        pass