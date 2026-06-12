"""Send locally rendered videos to Telegram WITHOUT approve buttons.

For videos rendered on this machine (no cloud artifact, so the YouTube button
would dangle). Usage:
    python automation/send_local.py <day_dir> <story_id> [note] [--force]
--force re-sends a story the delivered ledger says already went out.
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dedupe
import telegram_bot

argv = [a for a in sys.argv[1:] if a != "--force"]
force = "--force" in sys.argv
day_dir, story_id = Path(argv[0]), argv[1]
note = argv[2] if len(argv) > 2 else ""
chat_id = os.environ["TELEGRAM_CHAT_ID"]
caption = (day_dir / f"{story_id}-caption.txt").read_text(encoding="utf-8")
story = json.loads((day_dir / f"{story_id}.json").read_text(encoding="utf-8"))

ledger = dedupe.load()
sig = dedupe.story_tokens(story)
dup = dedupe.duplicate_of(story_id, sig, ledger)
if dup and not force:
    sys.exit(f"NOT sent: {story_id} duplicates already-delivered {dup} "
             "(re-run with --force to send anyway)")

with open(day_dir / f"{story_id}.mp4", "rb") as fh:
    msg = telegram_bot.call(
        "sendVideo", files={"video": fh}, chat_id=chat_id,
        caption=f"Locally rendered - no buttons. {note}".strip())
if not dup:
    dedupe.record(ledger, story_id, sig)
telegram_bot.call("sendMessage", chat_id=chat_id, text=caption,
                  reply_to_message_id=msg["message_id"])
print(f"sent {story_id} (remember to commit automation/delivered.json)")
