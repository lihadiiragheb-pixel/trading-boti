import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(token: str, chat_id: str, message: str):
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال إشعار تلجرام: {e}")
