from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from keyboards import get_main_menu
import sqlite3
import os

router = Router()
DB_NAME = "database.db"

@router.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_") | F.data.startswith("ban_"))
async def process_admin_action(callback: CallbackQuery, bot: Bot):
    action, user_id_str = callback.data.split("_")
    user_id = int(user_id_str)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if action == "approve":
        cursor.execute("UPDATE users SET is_trusted = 1, credits = credits + 1 WHERE user_id = ?", (user_id,))
        cursor.execute("INSERT INTO ledger (user_id, amount, description) VALUES (?, 1, 'Initial approval reward')", (user_id,))
        cursor.execute("UPDATE items SET status = 'approved' WHERE user_id = ? AND status = 'pending'", (user_id,))
        
        cursor.execute("SELECT id, file_type, file_id FROM items WHERE user_id = ? AND status = 'approved'", (user_id,))
        approved_items = cursor.fetchall()
        
        channel_1 = os.getenv("BACKUP_CHANNEL_ID_1")
        channel_2 = os.getenv("BACKUP_CHANNEL_ID_2")
        
        for item_id, file_type, file_id in approved_items:
            if channel_1:
                try:
                    if file_type == 'video':
                        msg1 = await bot.send_video(channel_1, file_id)
                    elif file_type == 'photo':
                        msg1 = await bot.send_photo(channel_1, file_id)
                    else:
                        msg1 = await bot.send_document(channel_1, file_id)
                    cursor.execute("INSERT INTO item_copies (item_id, channel_index, message_id) VALUES (?, 1, ?)", (item_id, msg1.message_id))
                except Exception as e:
                    print(f"Backup channel 1 error: {e}")
                    
            if channel_2:
                try:
                    if file_type == 'video':
                        msg2 = await bot.send_video(channel_2, file_id)
                    elif file_type == 'photo':
                        msg2 = await bot.send_photo(channel_2, file_id)
                    else:
                        msg2 = await bot.send_document(channel_2, file_id)
                    cursor.execute("INSERT INTO item_copies (item_id, channel_index, message_id) VALUES (?, 2, ?)", (item_id, msg2.message_id))
                except Exception as e:
                    print(f"Backup channel 2 error: {e}")
                    
        conn.commit()
        
        await callback.message.edit_text(f"✅ Paket tasdiqlandi! Foydalanuvchi (ID: {user_id}) trusted qilindi va 2 ta zaxira kanalga nusxalandi.")
        try:
            await bot.send_message(
                user_id, 
                "🎉 Sizning yuborgan paketingiz admin tomonidan tasdiqlandi! Sizga 1 kredit berildi va asosiy menyu ochildi.",
                reply_markup=get_main_menu()
            )
        except:
            pass
            
    elif action == "reject":
        cursor.execute("UPDATE items SET status = 'rejected' WHERE user_id = ? AND status = 'pending'", (user_id,))
        conn.commit()
        await callback.message.edit_text(f"❌ Paket rad etildi (Foydalanuvchi ID: {user_id}).")
        try:
            await bot.send_message(user_id, "❌ Afsuski, yuborgan paketingiz talablarga javob bermagani uchun rad etildi.")
        except:
            pass
            
    elif action == "ban":
        cursor.execute("UPDATE users SET state = 'blocked' WHERE user_id = ?", (user_id,))
        conn.commit()
        await callback.message.edit_text(f"🚫 Foydalanuvchi bloklandi (ID: {user_id}).")
        try:
            await bot.send_message(user_id, "🚫 Siz qoidabuzarlik uchun botdan bloklandingiz.")
        except:
            pass
        
    conn.close()
    await callback.answer()
