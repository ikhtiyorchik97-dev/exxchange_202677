# handlers/request.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_user, get_connection
from i18n import get_text

router = Router()


@router.message(F.text.in_(["📥 Kontent olish", "📥 Получить контент", "📥 Get content", "📥 Получить контент"]))
async def cmd_get_content(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)

    if not user:
        await message.answer("⚠️ Avval ro'yxatdan o'ting (/start).")
        return

    if user['state'] == 'blocked':
        await message.answer("🚫 Siz bloklangansiz.")
        return

    if user['credits'] < 1:
        await message.answer("❌ Sizda yetarli kredit yo'q! Kontent olish uchun avval botga yangi fayl yuboring.")
        return

    lang = user['language']
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Video", callback_data="get_video"),
            InlineKeyboardButton(text="🖼 Rasm", callback_data="get_photo")
        ]
    ])
    if user['is_trusted']:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="📦 Arxiv", callback_data="get_archive")])

    await message.answer("📥 Qanday turdagi kontent olmoqchisiz? Tanlang:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("get_"))
async def process_get_content_type(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    content_type = callback.data.split("_")[1]

    conn = get_connection()
    cursor = conn.cursor()

    # 1. Kreditni qayta tekshirish
    cursor.execute("SELECT credits FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row or row['credits'] < 1:
        await callback.answer("❌ Kredit yetarli emas!", show_alert=True)
        conn.close()
        return

    # 2. Bazadan mos faylni topish (PDF 7-bo'lim)
    # Shartlar: approved, o'ziniki emas, oldin yuborilmagan, unavailable emas
    query = """
        SELECT i.id 
        FROM items i
        WHERE i.file_type = ? 
          AND i.status = 'approved' 
          AND i.user_id != ?
          AND i.id NOT IN (SELECT item_id FROM deliveries WHERE user_id = ?)
          AND i.id NOT IN (SELECT item_id FROM send_queue WHERE user_id = ? AND status IN ('pending', 'processing'))
        LIMIT 1
    """
    cursor.execute(query, (content_type, user_id, user_id, user_id))
    item = cursor.fetchone()

    if not item:
        await callback.message.answer(
            "⚠️ Hozircha sizga yuborish uchun yangi kontent topilmadi. Keyinroq urinib ko'ring.")
        conn.close()
        await callback.answer()
        return

    item_id = item['id']

    # 3. Navbatga qo'shish
    cursor.execute("INSERT INTO send_queue (user_id, item_id, status) VALUES (?, ?, 'pending')", (user_id, item_id))
    conn.commit()
    conn.close()

    # 4. Foydalanuvchiga xabar berish
    report_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚨 Shikoyat qilish (Report)", callback_data=f"report_{item_id}")]
    ])
    await callback.message.answer(
        "⏳ So'rovingiz navbatga qo'shildi. Fayl tez orada yuboriladi...",
        reply_markup=report_kb
    )
    await callback.answer()