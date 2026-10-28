# Telegram Almashish Boti - Ultimate Failover Versiya (1-7 Bosqichlar + Zaxira Bot va Ikki Kanal)

Bu arxivda botning barcha bosqichlari to'liq jamlangan:
1. Til tanlash (7 til) va `/start` onboarding.
2. Telegram Mini App va Cloudflare Turnstile orqali CAPTCHA tekshiruvi.
3. Fayllarni qabul qilish, zararli dasturlarni bloklash, dublikat va qora ro'yxat tekshiruvi hamda Flood Control.
4. Admin guruhida paketlarni tasdiqlash, rad etish va ban qilish.
5. Kredit tizimi va kontent olish (`[Video]`, `[Rasm]`, `[Arxiv]`).
6. Shikoyat tizimi (`Report`) va qora ro'yxatga olish.
7. Ikki ta zaxira kanalga (`BACKUP_CHANNEL_ID_1` va `BACKUP_CHANNEL_ID_2`) bir vaqtda nusxalash hamda zaxira bot (`backup_main.py`) imkoniyati.

## O'rnatish va Ishga tushirish:
1. `pip install -r requirements.txt` orqali kerakli kutubxonalarni o'rnating.
2. `.env.example` faylini `.env` deb nomlang va token hamda kanal ID'larini kiriting.
3. `webapp/index.html` ichiga o'zingizning Cloudflare Turnstile `Site Key` ni kiriting.
4. Asosiy bot uchun: `python main.py`
5. Asosiy bot spamga tushsa, zaxira bot uchun: `python backup_main.py`
