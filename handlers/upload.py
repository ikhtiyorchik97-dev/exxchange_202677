from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user, add_item, is_blacklisted
import os
import time

router = Router()
BAD_EXTENSIONS = ['.exe', '.apk', '.msi', '.bat', '.sh', '.scr', '.pif', '.com']
user_last_upload = {}

@router.message(F.document | F.video | F.photo)
async def handle_incoming_files(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    now = time.time()
    if user_id in user_last_upload and now - user_last_upload[user_id] < 3:
        await message.answer("⚠️ Juda tez-tez fayl yuboryapsiz! Biroz kuting.")
        return
    user_last_upload[user_id] = now

    user = get_user(user_id)
    if not user or user[2] != 'verified':
        await message.answer("⚠️ Fayl yuborish uchun avval botdan to'liq ro'yxatdan o'tishingiz kerak (/start).")
        return
    
    if user[2] == 'blocked':
        await message.answer("🚫 Siz botdan foydalanishdan bloklangansiz.")
        return
    
    is_trusted = user[3]
    can_send_archives = user[4]
    
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
        
        if duration < 15:
            await message.answer("❌ Video juda qisqa! Davomiyligi kamida 15 soniya bo'lishi kerak.")
            return
            
    elif message.photo:
        file_type = 'photo'
        photo = message.photo[-1]
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id
        file_size = photo.file_size or 0
        
    elif message.document:
        document = message.document
        file_name = document.file_name.lower() if document.file_name else ""
        file_id = document.file_id
        file_unique_id = document.file_unique_id
        file_size = document.file_size or 0
        
        if any(file_name.endswith(ext) for ext in BAD_EXTENSIONS):
            await message.answer("❌ Bu turdagi bajariladigan fayllarni yuborish qat'iyan taqiqlangan!")
            return
            
        if any(file_name.endswith(ext) for ext in ['.zip', '.rar', '.7z']):
            if not is_trusted and not can_send_archives:
                await message.answer("❌ Arxiv fayllarini faqat ishonchli foydalanuvchilar yuborishi mumkin!")
                return
            file_type = 'archive'
        else:
            file_type = 'document'

    if is_blacklisted(file_unique_id):
        await message.answer("❌ Bu fayl qora ro'yxatga kiritilgan!")
        return

    success = add_item(user_id, file_type, file_id, file_unique_id, duration, file_size)
    if not success:
        await message.answer("⚠️ Bu fayl oldin bazaga yuborilgan (dublikat)!")
        return

    if is_trusted:
        await message.answer("✅ Faylingiz qabul qilindi va avtomatik tasdiqlandi!")
    else:
        admin_group_id = os.getenv("ADMIN_GROUP_ID")
        if admin_group_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user_id}")
                ],
                [
                    InlineKeyboardButton(text="🚫 Ban qilish", callback_data=f"ban_{user_id}")
                ]
            ])
            await bot.send_message(
                admin_group_id,
                f"📥 **Yangi paket tekshiruvi!**\nFoydalanuvchi ID: <code>{user_id}</code>\nFayl turi: {file_type}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        await message.answer("⏳ Faylingiz qabul qilindi va adminlar tekshiruviga yuborildi.")
