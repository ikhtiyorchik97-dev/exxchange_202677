# handlers/review.py
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from db import get_connection, create_or_update_user
from config import config
from keyboards import get_main_menu

router = Router()


@router.callback_query(
    F.data.startswith("approve_batch_") | F.data.startswith("reject_batch_") | F.data.startswith("ban_user_"))
async def process_admin_action(callback: CallbackQuery, bot: Bot):
    action_data = callback.data.split("_")
    action = action_data[0]

    conn = get_connection()
    cursor = conn.cursor()

    if action == "approve" and action_data[1] == "batch":
        batch_id = int(action_data[2])

        # Paketni olish
        cursor.execute("SELECT user_id FROM batches WHERE id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch:
            await callback.answer("Paket topilmadi!", show_alert=True)
            return
        user_id = batch['user_id']

        # Paketdagi tayyor fayllar
        cursor.execute("SELECT id, file_id, file_type FROM items WHERE batch_id = ? AND status = 'pending'",
                       (batch_id,))
        items = cursor.fetchall()

        if not items:
            await callback.answer("Bu paketda fayl yo'q!", show_alert=True)
            return

        total_files = len(items)

        # 1. Holatni approved ga o'tkazish
        cursor.execute("UPDATE batches SET status = 'approved' WHERE id = ?", (batch_id,))
        cursor.execute("UPDATE items SET status = 'approved' WHERE batch_id = ?", (batch_id,))

        # 2. Foydalanuvchini trusted qilish va kredit berish
        cursor.execute(
            "UPDATE users SET is_trusted = 1, can_send_archives = 1, credits = credits + ? WHERE user_id = ?",
            (total_files, user_id))
        cursor.execute("INSERT INTO ledger (user_id, amount, description) VALUES (?, ?, ?)",
                       (user_id, total_files, f"Batch {batch_id} approved"))

        # 3. Kanallarga nusxalash (PDF 9-bo'lim)
        # Bu joyda copyMessage ishlatiladi, lekin hozircha bizda manba xabar yo'q. 
        # Bizning bazada faqat file_id bor. Shuning uchun send_video/send_photo ishlatamiz.
        # (Keyinchalik 8-bosqichda kanallardan to'g'ridan-to'g'ri forward qilishni qo'shamiz).

        channels = [
            config.CHANNEL_CATALOG_ID,
            config.CHANNEL_INBOX_ID,
            config.CHANNEL_BACKUP_ID,
            config.CHANNEL_CATALOG_BACKUP_ID
        ]

        for item in items:
            item_id, file_id, file_type = item['id'], item['file_id'], item['file_type']

            for idx, channel_id in enumerate(channels, start=1):
                if not channel_id:
                    continue
                try:
                    if file_type == 'video':
                        msg = await bot.send_video(channel_id, file_id)
                    elif file_type == 'photo':
                        msg = await bot.send_photo(channel_id, file_id)
                    else:
                        msg = await bot.send_document(channel_id, file_id)

                    cursor.execute("INSERT INTO item_copies (item_id, channel_index, message_id) VALUES (?, ?, ?)",
                                   (item_id, idx, msg.message_id))
                except Exception as e:
                    print(f"Kanal {idx} ga yuborishda xato: {e}")

        conn.commit()
        conn.close()

        await callback.message.edit_text(
            f"✅ Paket tasdiqlandi! {total_files} ta fayl kanallarga nusxalandi va foydalanuvchiga {total_files} kredit berildi.")

        # Foydalanuvchiga xabar
        user = get_connection().execute("SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
        lang = user['language'] if user else 'uz'
        try:
            await bot.send_message(user_id, f"🎉 Paketingiz tasdiqlandi! Sizga {total_files} kredit berildi.",
                                   reply_markup=get_main_menu(lang))
        except:
            pass

    elif action == "reject" and action_data[1] == "batch":
        batch_id = int(action_data[2])
        cursor.execute("SELECT user_id FROM batches WHERE id = ?", (batch_id,))
        batch = cursor.fetchone()
        if not batch: return
        user_id = batch['user_id']

        cursor.execute("UPDATE batches SET status = 'rejected' WHERE id = ?", (batch_id,))
        cursor.execute("UPDATE items SET status = 'rejected' WHERE batch_id = ?", (batch_id,))
        conn.commit()
        conn.close()

        await callback.message.edit_text("❌ Paket rad etildi.")
        try:
            await bot.send_message(user_id,
                                   "❌ Afsuski, yuborgan paketingiz talablarga javob bermagani uchun rad etildi.")
        except:
            pass

    elif action == "ban":
        user_id = int(action_data[2])
        cursor.execute("UPDATE users SET state = 'blocked' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        await callback.message.edit_text("🚫 Foydalanuvchi bloklandi.")
        try:
            await bot.send_message(user_id, "🚫 Siz qoidabuzarlik uchun botdan bloklandingiz.")
        except:
            pass

    await callback.answer()