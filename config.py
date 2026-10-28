# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 1. Bot tokenlari
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    BACKUP_BOT_TOKEN = os.getenv("BACKUP_BOT_TOKEN")
    
    # 2. Kanallar
    CHANNEL_CATALOG_ID = int(os.getenv("CHANNEL_CATALOG_ID", 0))
    CHANNEL_INBOX_ID = int(os.getenv("CHANNEL_INBOX_ID", 0))
    CHANNEL_BACKUP_ID = int(os.getenv("CHANNEL_BACKUP_ID", 0))
    CHANNEL_CATALOG_BACKUP_ID = int(os.getenv("CHANNEL_CATALOG_BACKUP_ID", 0))
    
    # 3. Admin guruhi
    ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", 0))
    
    # Admin ID lari (vergul bilan ajratilgan bo'lsa, ro'yxatga aylantiramiz)
    ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
    ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_STR.split(",") if x.strip()]
    
    # 4. Web App va CAPTCHA (Mana shu qism yetishmayotgan edi!)
    WEB_APP_URL = os.getenv("WEB_APP_URL", "https://example.com/")
    TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
    
    # 5. Qo'shimcha sozlamalar
    DB_NAME = os.getenv("DB_NAME", "database.db")
    DELETE_AFTER_SECONDS = int(os.getenv("DELETE_AFTER_SECONDS", 0))
    VERIFIED_DAYS = 30

# Klassdan obyekt yaratamiz (butun loyiha shuni ishlatadi)
config = Config()
