from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_language_keyboard():
    languages = [
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
    texts = {
        "ru": {"cont": "Продолжить", "exit": "Выйти"},
        "en": {"cont": "Continue", "exit": "Exit"},
        "es": {"cont": "Continuar", "exit": "Salir"},
        "fr": {"cont": "Continuer", "exit": "Quitter"},
        "ar": {"cont": "متابعة", "exit": "خروج"},
        "zh": {"cont": "继续", "exit": "退出"},
        "hi": {"cont": "जारी रखें", "exit": "बाहर निकलें"}
    }
    t = texts.get(lang_code, texts["en"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t["cont"], callback_data="btn_continue"),
            InlineKeyboardButton(text=t["exit"], callback_data="btn_exit")
        ]
    ])
    return keyboard

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Kontent olish")]
        ],
        resize_keyboard=True
    )
