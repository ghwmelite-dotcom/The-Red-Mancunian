"""Thin Telegram Bot API wrapper + alert CLI.

Usage from workflows:  python automation/telegram_bot.py alert "message text"
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import sys

import requests


def call(method: str, files=None, **params) -> dict:
    """Post to the Bot API; files is a requests-style multipart dict (e.g. sendVideo)."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    resp = requests.post(f"https://api.telegram.org/bot{token}/{method}",
                         data=params, files=files, timeout=120)
    resp.raise_for_status()
    return resp.json()["result"]


def send_alert(text: str) -> None:
    call("sendMessage", chat_id=os.environ["TELEGRAM_CHAT_ID"], text=text)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "alert":
        send_alert(sys.argv[2])
    else:
        sys.exit("usage: telegram_bot.py alert <text>")
