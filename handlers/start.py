from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os
from db import create_or_update_user
from keyboards import get_language_keyboard, get_description_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    create_or_update_user(user_id, state="new")
    
    text = (
        "Please select your language / Iltimos, tilingizni tanlang / "
        "Пожалуйста, выберите язык:"
    )
    await message.answer(text, reply_markup=get_language_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]
    
    create_or_update_user(user_id, language=lang_code, state="lang_selected")
    
    descriptions = {
        "en": "Welcome! This bot is designed for exchanging educational content. Rules: 18+, copyright compliance.\n\nClick Continue to proceed.",
        "ru": "Добро пожаловать! Правила: 18+, соблюдение авторских прав.\n\nНажмите Продолжить.",
        "es": "¡Bienvenido! Este bot está diseñado para el intercambio de contenido educativo. Reglas: 18+, cumplimiento de derechos de autor.\n\nHaga clic en Continuar.",
        "fr": "Bienvenue ! Ce bot est conçu pour l'échange de contenu éducatif. Règles : 18+, respect des droits d'auteur.\n\nCliquez sur Continuer.",
        "ar": "مرحباً! تم تصميم هذا الروبوت لتبادل المحتوى التعليمي. القواعد: 18+، الالتزام بحقوق النشر.\n\nانقر فوق متابعة للمتابعة.",
        "zh": "欢迎！此机器人用于交换教育内容。规则：18+，遵守版权.\n点击继续。",
        "hi": "स्वागत है! यह बॉट शैक्षणिक सामग्री के आदान-प्रदान के लिए है। नियम: 18+, कॉपीराइट का पालन।\n\nजारी रखें पर क्लिक करें."
    }
    desc_text = descriptions.get(lang_code, descriptions["en"])
    
    await callback.message.edit_text(desc_text, reply_markup=get_description_keyboard(lang_code))
    await callback.answer()

@router.callback_query(F.data == "btn_exit")
async def process_exit(callback: CallbackQuery):
    await callback.message.edit_text("Botdan foydalanish bekor qilindi. Qaytadan boshlash uchun /start bosing.")
    await callback.answer()

@router.callback_query(F.data == "btn_continue")
async def process_continue(callback: CallbackQuery):
    user_id = callback.from_user.id
    create_or_update_user(user_id, state="intent_credits")
    
    web_app_url = os.getenv("WEB_APP_URL", "https://your-domain.alwaysdata.net/")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛡 CAPTCHA dan o'tish", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await callback.message.edit_text(
        "Shartlar qabul qilindi. Tasdiqlash uchun quyidagi tugmani bosing:",
        reply_markup=keyboard
    )
    await callback.answer()
