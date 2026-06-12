"""Send locally rendered videos to Telegram WITHOUT approve buttons.

For videos rendered on this machine (no cloud artifact, so the YouTube button
would dangle). Usage:
    python automation/send_local.py <day_dir> <story_id> [note]
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telegram_bot

day_dir, story_id = Path(sys.argv[1]), sys.argv[2]
note = sys.argv[3] if len(sys.argv) > 3 else ""
chat_id = os.environ["TELEGRAM_CHAT_ID"]
caption = (day_dir / f"{story_id}-caption.txt").read_text(encoding="utf-8")

with open(day_dir / f"{story_id}.mp4", "rb") as fh:
    msg = telegram_bot.call(
        "sendVideo", files={"video": fh}, chat_id=chat_id,
        caption=f"Locally rendered - no buttons. {note}".strip())
telegram_bot.call("sendMessage", chat_id=chat_id, text=caption,
                  reply_to_message_id=msg["message_id"])
print(f"sent {story_id}")
