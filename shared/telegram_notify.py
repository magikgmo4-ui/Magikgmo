import os
import requests
import html
def send_telegram(message: str):
    token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("Telegram env vars not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": html.escape(message),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
