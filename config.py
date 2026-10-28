import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    # ... qolgan sozlamalar ...
    DB_NAME = os.getenv("DB_NAME", "database.db")

config = Config()
