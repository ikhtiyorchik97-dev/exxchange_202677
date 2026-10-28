# handlers/start.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from config import config
from db import get_user, create_or_update_user
from keyboards import get_language_keyboard, get_description_keyboard, get_captcha_keyboard
from i18n import get_text

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Bloklangan foydalanuvchini tekshirish
    user = get_user(user_id)
    if user and user['state'] == 'blocked':
        return

    # Agar allaqachon verified bo'lsa
    if user and user['state'] == 'verified':
        lang = user['language']
        await message.answer(get_text(lang, "verified_success"))
        return

    # Yangi foydalanuvchi
    create_or_update_user(user_id, state="new")

    text = get_text("uz", "choose_language")
    await message.answer(text, reply_markup=get_language_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]

    create_or_update_user(user_id, language=lang_code, state="lang_selected")

    desc_text = get_text(lang_code, "welcome_desc")
    await callback.message.edit_text(desc_text, reply_markup=get_description_keyboard(lang_code))
    await callback.answer()

@router.callback_query(F.data == "btn_exit")
async def process_exit(callback: CallbackQuery):
    user = get_user(callback.from_user.id)
    lang = user['language'] if user else 'uz'
    await callback.message.edit_text(get_text(lang, "exit_msg"))
    await callback.answer()

@router.callback_query(F.data == "btn_continue")
async def process_continue(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)

    if not user or user['state'] != 'lang_selected':
        await callback.answer("Xatolik yuz berdi. Iltimos /start buyrug'ini bosing.", show_alert=True)
        return

    lang = user['language']
    create_or_update_user(user_id, state="intent_confirmed")

    # URL ni to'g'rilash va user_id ni qo'shish (fallback uchun)
    base_url = config.WEB_APP_URL
    if not base_url.endswith('/'):
        base_url += '/'
    web_app_url = f"{base_url}?user_id={user_id}"

    await callback.message.edit_text(
        get_text(lang, "captcha_prompt"),
        reply_markup=get_captcha_keyboard(lang, web_app_url)
    )
    await callback.answer()
