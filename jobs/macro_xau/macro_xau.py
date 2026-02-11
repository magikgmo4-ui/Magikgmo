#!/usr/bin/env python3
import os
import sys
import traceback
from datetime import datetime

#!/usr/bin/env python3
import sys
import traceback
from datetime import datetime

sys.path.append("/opt/trading/shared")
from telegram_notify import send_telegram

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # TODO: ta vraie logique trading
    signal = True

    if signal:
        send_telegram(f"🟡 <b>Macro XAU</b>\nSignal détecté à {now}")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception:
        try:
            send_telegram("❌ <b>Macro XAU — ERREUR</b>\n<pre>" + traceback.format_exc() + "</pre>")
        except Exception:
            pass
        sys.exit(1)

sys.path.append("/opt/trading/shared")
from telegram_notify import send_telegram

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === LOGIQUE TRADING ICI ===
    signal = True  # <-- mets ta vraie logique

    if signal:
        send_telegram(f"🟡 <b>Macro XAU</b>\nSignal détecté à {now}")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        msg = (
            "❌ <b>Macro XAU — ERREUR</b>\n"
            f"<pre>{traceback.format_exc()}</pre>"
        )
        try:
            send_telegram(msg)
        except Exception:
            pass
        sys.exit(1)

