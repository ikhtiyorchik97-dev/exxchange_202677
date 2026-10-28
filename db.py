# db.py
import sqlite3
import logging
from config import config

def get_connection():
    """Bazaga ulanish yaratadi. Har safar chaqirilganda yangi ulanish qaytaradi."""
    conn = sqlite3.connect(config.DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """schema.sql faylini o'qib, bazada jadvallarni yaratadi."""
    try:
        conn = get_connection()
        with open('schema.sql', 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()
        logging.info("Baza muvaffaqiyatli ishga tushirildi.")
    except Exception as e:
        logging.error(f"Bazani ishga tushirishda xato: {e}")

def get_user(user_id: int):
    """Foydalanuvchini ID si bo'yicha bazadan qidiradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_or_update_user(user_id: int, **kwargs):
    """Yangi foydalanuvchi yaratadi yoki mavjudining ma'lumotlarini yangilaydi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    
    for key, value in kwargs.items():
        # SQL Injection dan himoya qilish uchun faqat ruxsat etilgan ustunlarni yangilaymiz
        allowed_columns = ['language', 'state', 'is_trusted', 'can_send_archives', 'credits', 'verified_until', 'suspicion_score']
        if key in allowed_columns:
            cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
    
    conn.commit()
    conn.close()

def add_credits(user_id: int, amount: int, description: str):
    """Foydalanuvchiga kredit qo'shadi yoki ayiradi va buni ledgerga yozadi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("INSERT INTO ledger (user_id, amount, description) VALUES (?, ?, ?)", (user_id, amount, description))
    conn.commit()
    conn.close()

def is_blacklisted(file_unique_id: str):
    """Fayl qora ro'yxatda bor-yo'qligini tekshiradi."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM blacklist WHERE file_unique_id = ?", (file_unique_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None
