# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from i18n import get_text

def get_language_keyboard():
    languages = [
        ("🇺🇿 O'zbekcha", "lang_uz"),
        ("English", "lang_en"),
        ("Русский", "lang_ru"),
        ("中文", "lang_zh"),
        ("हिन्दी", "lang_hi"),
        ("العربية", "lang_ar"),
        ("Español", "lang_es"),
        ("Français", "lang_fr")
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for i in range(0, len(languages), 2):
        row = [InlineKeyboardButton(text=languages[i][0], callback_data=languages[i][1])]
        if i + 1 < len(languages):
            row.append(InlineKeyboardButton(text=languages[i+1][0], callback_data=languages[i+1][1]))
        keyboard.inline_keyboard.append(row)
    return keyboard

def get_description_keyboard(lang_code: str):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(lang_code, "btn_continue"), callback_data="btn_continue"),
            InlineKeyboardButton(text=get_text(lang_code, "btn_exit"), callback_data="btn_exit")
        ]
    ])
    return keyboard

def get_captcha_keyboard(lang_code: str, web_app_url: str):
    from aiogram.types import WebAppInfo
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(lang_code, "btn_captcha"), web_app=WebAppInfo(url=web_app_url))]
    ])
    return keyboard

def get_main_menu(lang_code: str):
    # PDFga muvofiq asosiy menyu (Reply yoki Inline bo'lishi mumkin, hozircha Reply qilamiz)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text(lang_code, "menu_upload")), KeyboardButton(text=get_text(lang_code, "menu_get"))],
            [KeyboardButton(text=get_text(lang_code, "menu_profile"))]
        ],
        resize_keyboard=True
    )
    return keyboard