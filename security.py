# security.py
import hmac
import hashlib
from urllib.parse import parse_qsl
from config import config
import aiohttp
import logging


def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Telegram WebApp initData ni HMAC-SHA256 orqali tekshiradi.
    Agar haqiqiy bo'lsa, foydalanuvchi ma'lumotlarini qaytaradi, aks holda None.
    """
    if not init_data:
        return None

    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data:
            return None

        received_hash = parsed_data.pop("hash")

        # Ma'lumotlarni saralash va birlashtirish
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # HMAC hisoblash (Telegram talab qilganidek)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=config.BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if calculated_hash == received_hash:
            # HMAC to'g'ri, endi user ma'lumotlarini qaytaramiz
            if "user" in parsed_data:
                import json
                return json.loads(parsed_data["user"])
        return None
    except Exception as e:
        logging.error(f"initData verify error: {e}")
        return None


async def verify_turnstile(token: str) -> bool:
    """
    Cloudflare Turnstile tokenni server orqali tekshiradi.
    """
    if not config.TURNSTILE_SECRET_KEY:
        logging.error("TURNSTILE_SECRET_KEY topilmadi!")
        return False

    async with aiohttp.ClientSession() as session:
        async with session.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": config.TURNSTILE_SECRET_KEY,
                    "response": token
                }
        ) as resp:
            result = await resp.json()
            return result.get("success", False)