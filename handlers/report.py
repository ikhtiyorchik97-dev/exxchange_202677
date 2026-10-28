# handlers/report.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_connection, get_user
from config import config
import logging

router = Router()


@router.callback_query(F.data.startswith("report_"))
async def process_report(callback: CallbackQuery, bot: Bot):
    item_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    conn = get_connection()
    cursor = conn.cursor()

    # Shikoyatni saqlash
    cursor.execute("INSERT INTO reports (user_id, item_id, reason) VALUES (?, ?, 'User complaint')", (user_id, item_id))
    conn.commit()
    conn.close()

    await callback.message.answer("🚨 Shikoyatingiz qabul qilindi. Adminlar tez orada ko'rib chiqadi. Rahmat!")

    # Admin guruhiga xabar berish
    if config.ADMIN_GROUP_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Faylni o'chirish", callback_data=f"blacklist_item_{item_id}")]
        ])
        try:
            await bot.send_message(
                config.ADMIN_GROUP_ID,
                f"🚨 <b>Yangi shikoyat!</b>\nFoydalanuvchi ID: <code>{user_id}</code>\nFayl ID: <code>{item_id}</code>",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Admin guruhiga shikoyat yuborishda xato: {e}")

    await callback.answer()


@router.callback_query(F.data.startswith("blacklist_item_"))
async def process_blacklist_item(callback: CallbackQuery, bot: Bot):
    item_id = int(callback.data.split("_")[2])

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Faylni bazadan topish
    cursor.execute("SELECT file_unique_id FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()

    if not row:
        await callback.message.edit_text("⚠️ Fayl topilmadi.")
        conn.close()
        return

    file_unique_id = row['file_unique_id']

    # 2. Qora ro'yxatga qo'shish
    cursor.execute("INSERT OR IGNORE INTO blacklist (file_unique_id, reason) VALUES (?, 'Admin banned')",
                   (file_unique_id,))

    # 3. Fayl holatini removed ga o'zgartirish
    cursor.execute("UPDATE items SET status = 'removed' WHERE id = ?", (item_id,))

    # 4. Kanallardagi nusxalarni o'chirish (PDF 9-jadval)
    cursor.execute("SELECT channel_index, message_id FROM item_copies WHERE item_id = ?", (item_id,))
    copies = cursor.fetchall()

    channels = {
        1: config.CHANNEL_CATALOG_ID,
        2: config.CHANNEL_INBOX_ID,
        3: config.CHANNEL_BACKUP_ID,
        4: config.CHANNEL_CATALOG_BACKUP_ID
    }

    for copy in copies:
        ch_id = channels.get(copy['channel_index'])
        if ch_id:
            try:
                await bot.delete_message(chat_id=ch_id, message_id=copy['message_id'])
            except Exception:
                pass

    conn.commit()
    conn.close()

    await callback.message.edit_text(f"✅ Fayl (ID: {item_id}) hamma kanaldan o'chirildi va qora ro'yxatga kiritildi.")
    await callback.answer()