from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os

router = Router()
DB_NAME = "database.db"

@router.callback_query(F.data.startswith("report_"))
async def process_report(callback: CallbackQuery, bot: Bot):
    item_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reports (user_id, item_id, reason) VALUES (?, ?, 'User complaint')", (user_id, item_id))
    conn.commit()
    conn.close()
    
    await callback.message.answer("🚨 Shikoyatingiz adminga yuborildi. Tez orada ko'rib chiqiladi. Rahmat!")
    
    admin_group_id = os.getenv("ADMIN_GROUP_ID")
    if admin_group_id:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Faylni o'chirish / Qora ro'yxatga", callback_data=f"blacklist_item_{item_id}")
            ]
        ])
        try:
            await bot.send_message(
                admin_group_id,
                f"🚨 **Yangi shikoyat (Report)!**\nFoydalanuvchi ID: <code>{user_id}</code>\nFayl ID: {item_id}",
                reply_markup=kb,
                parse_mode="HTML"
            )
        except:
            pass
            
    await callback.answer()

@router.callback_query(F.data.startswith("blacklist_item_"))
async def process_blacklist_item(callback: CallbackQuery):
    item_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_unique_id FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    
    if row:
        file_unique_id = row[0]
        cursor.execute("INSERT OR IGNORE INTO blacklist (file_unique_id) VALUES (?)", (file_unique_id,))
        cursor.execute("UPDATE items SET status = 'blacklisted' WHERE id = ?", (item_id,))
        conn.commit()
        await callback.message.edit_text(f"✅ Fayl (ID: {item_id}) qora ro'yxatga qo'shildi va bloklandi.")
    else:
        await callback.message.edit_text("⚠️ Fayl topilmadi.")
        
    conn.close()
    await callback.answer()
