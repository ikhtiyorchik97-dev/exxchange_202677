from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3

router = Router()
DB_NAME = "database.db"

@router.message(F.text == "📥 Kontent olish")
async def cmd_get_content(message: Message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT credits, is_trusted, state FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        await message.answer("⚠️ Avval ro'yxatdan o'ting (/start).")
        conn.close()
        return
        
    credits, is_trusted, state = user[0], user[1], user[2]
    
    if state == 'blocked':
        await message.answer("🚫 Siz bloklangansiz.")
        conn.close()
        return
        
    if credits < 1:
        await message.answer("❌ Sizda yetarli kredit yo'q! Kontent olish uchun avval botga yangi fayl yuboring.")
        conn.close()
        return
        
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data="get_video"),
            InlineKeyboardButton(text="🖼 Rasm", callback_data="get_photo")
        ]
    ])
    if is_trusted:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="📦 Arxiv (Faqat trusted)", callback_data="get_archive")])
        
    await message.answer("📥 Qanday turdagi kontent olmoqchisiz? Tanlang:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("get_"))
async def process_get_content_type(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    content_type = callback.data.split("_")[1]
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row[0] < 1:
        await callback.answer("❌ Kredit yetarli emas!", show_alert=True)
        conn.close()
        return
        
    cursor.execute("""
        SELECT id, file_id FROM items 
        WHERE file_type = ? AND status = 'approved' AND user_id != ?
        AND id NOT IN (SELECT item_id FROM deliveries WHERE user_id = ?)
        LIMIT 1
    """, (content_type, user_id, user_id))
    
    item = cursor.fetchone()
    
    if not item:
        await callback.message.answer("⚠️ Hozircha sizga yuborish uchun yangi kontent topilmadi. Keyinroq urinib ko'ring.")
        conn.close()
        await callback.answer()
        return
        
    item_id, file_id = item[0], item[1]
    
    try:
        if content_type == 'archive':
            await bot.send_document(user_id, file_id)
        elif content_type == 'video':
            await bot.send_video(user_id, file_id)
        else:
            await bot.send_photo(user_id, file_id)
            
        cursor.execute("INSERT INTO deliveries (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
        cursor.execute("UPDATE users SET credits = credits - 1 WHERE user_id = ?", (user_id,))
        cursor.execute("INSERT INTO ledger (user_id, amount, description) VALUES (?, -1, ?)", (user_id, f"Item {item_id} fetched"))
        conn.commit()
        
        report_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚨 Shikoyat qilish (Report)", callback_data=f"report_{item_id}")]
        ])
        await bot.send_message(user_id, "✅ Kontent muvaffaqiyatli yuborildi! 1 kredit yechildi.", reply_markup=report_kb)
    except Exception as e:
        await callback.message.answer("❌ Faylni yuborishda xatolik yuz berdi.")
        
    conn.close()
    await callback.answer()
