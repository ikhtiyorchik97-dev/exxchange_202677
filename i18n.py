# i18n.py
import json
import os
import logging

translations = {}

def load_locales():
    """locales papkasidagi barcha JSON fayllarni o'qib, xotiraga yuklaydi."""
    global translations
    locales_dir = "locales"
    
    if not os.path.exists(locales_dir):
        logging.warning(f"{locales_dir} papkasi topilmadi. Tillar yuklanmadi.")
        return
        
    for filename in os.listdir(locales_dir):
        if filename.endswith(".json"):
            lang = filename.split(".")[0]
            try:
                with open(os.path.join(locales_dir, filename), "r", encoding="utf-8") as f:
                    translations[lang] = json.load(f)
            except Exception as e:
                logging.error(f"Til faylini o'qishda xato ({filename}): {e}")

def get_text(lang: str, key: str, **kwargs) -> str:
    """Berilgan til va kalit bo'yicha matnni qaytaradi."""
    global translations
    
    # Agar tillar hali yuklanmagan bo'lsa, yuklaymiz
    if not translations:
        load_locales()
    
    # Tanlangan tilni olamiz, agar u bo'lmasa ingliz tilini (en) olamiz
    lang_dict = translations.get(lang, translations.get("en", {}))
    text = lang_dict.get(key)
    
    # Agar matn topilmasa, ingliz tilidan qidiramiz
    if text is None and lang != "en":
        text = translations.get("en", {}).get(key)
        
    # Agar u ham bo'lmasa, kalitning o'zini qaytaramiz (dastur qulamasligi uchun)
    if text is None:
        return f"MISSING_TEXT: {key}"
        
    # Matn ichidagi {o'zgaruvchi} larni almashtirish
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception as e:
            logging.error(f"Matnni formatlashda xato ({key}): {e}")
            
    return text
