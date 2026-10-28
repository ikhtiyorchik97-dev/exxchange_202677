# handlers/upload.py
from aiogram import Router, F, Bot
from aiogram.types import Message
from db import get_user, get_connection, is_blacklisted
from config import config
from i18n import get_text
import time

router = Router()
BAD_EXTENSIONS = ['.exe', '.apk', '.msi', '.bat', '.sh', '.scr', '.pif', '.com']
user_last_upload = {}


@router.message(F.document | F.video | F.photo)
async def handle_incoming_files(message: Message, bot: Bot):
    user_id = message.from_user.id

    # 1. Tezlik cheklovi (Flood control) - 3 soniya
    now = time.time()
    if user_id in user_last_upload and now - user_last_upload[user_id] < 3:
        await message.answer("⚠️ Juda tez-tez fayl yuboryapsiz! Biroz kuting.")
        return
    user_last_upload[user_id] = now

    user = get_user(user_id)
    if not user or user['state'] != 'verified':
        await message.answer("⚠️ Fayl yuborish uchun avval botdan to'liq ro'yxatdan o'tishingiz kerak (/start).")
        return

    is_trusted = user['is_trusted']
    can_send_archives = user['can_send_archives']
    lang = user['language']

    file_type = None
    file_id = None
    file_unique_id = None
    duration = 0
    file_size = 0

    # 2. Turini aniqlash
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

    # 3. Qora ro'yxat tekshiruvi
    if is_blacklisted(file_unique_id):
        await message.answer("❌ Bu fayl qora ro'yxatga kiritilgan!")
        return

    # 4. Paketga qo'shish (Batch logic)
    conn = get_connection()
    cursor = conn.cursor()

    # Foydalanuvchining "collecting" holatidagi paketini qidiramiz
    cursor.execute("SELECT id FROM batches WHERE user_id = ? AND status = 'collecting' ORDER BY id DESC LIMIT 1",
                   (user_id,))
    batch = cursor.fetchone()

    if not batch:
        # Yangi paket yaratamiz
        cursor.execute("INSERT INTO batches (user_id, status) VALUES (?, 'collecting')", (user_id,))
        batch_id = cursor.lastrowid
    else:
        batch_id = batch['id']

    # Faylni bazaga yozamiz
    try:
        cursor.execute("""
            INSERT INTO items (user_id, batch_id, file_type, file_id, file_unique_id, duration, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, batch_id, file_type, file_id, file_unique_id, duration, file_size))
        conn.commit()
    except Exception as e:
        # Dublikat bo'lsa (UNIQUE constraint)
        await message.answer("⚠️ Bu fayl oldin bazaga yuborilgan (dublikat)!")
        conn.close()
        return

    conn.close()

    # 5. Javob berish
    if is_trusted:
        await message.answer(
            "✅ Faylingiz qabul qilindi. Paketni yakunlash uchun [Yuborishni tugatdim] tugmasini bosing yoki 15 soniya kuting.")
    else:
        await message.answer(
            "📥 Fayl qabul qilindi. Yana fayl yuborishingiz mumkin. Paketni yakunlash uchun [Yuborishni tugatdim] tugmasini bosing.")

    # 6. Paketni avtomatik yakunlash uchun ishchini ishga tushirish
    # (Eslatma: bu har bir fayl kelganda ishga tushadi va 15 soniya kutadi. 
    # Agar shu vaqt ichida yangi fayl kelsa, u yangi batch_id olmaydi, balki mavjudiga qo'shiladi. 
    # Hozircha soddalik uchun har safar chaqiramiz).
    from workers.batch_finalizer import finalize_batch
    import asyncio
    asyncio.create_task(finalize_batch(batch_id, bot))