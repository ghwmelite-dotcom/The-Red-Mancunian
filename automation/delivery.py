"""Send rendered story videos to Telegram with approve/reject buttons.

Usage (from the editor workflow):
    python automation/delivery.py --run-id 123456 --day-dir tiktok/output/2026-06-11 \
        --ids "2026-06-11-story-a 2026-06-11-story-b"

The TikTok MP4 goes inline (it IS the manual-posting copy); the caption is a
second plain message so it can be copied with one tap. Buttons carry
"<action>:<run_id>:<story_id>" - Telegram caps callback_data at 64 bytes.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import telegram_bot


def build_callback(action: str, run_id: str, story_id: str) -> str:
    data = f"{action}:{run_id}:{story_id}"
    if len(data.encode()) > 64:
        raise ValueError(
            f"callback_data over Telegram's 64-byte limit: {data!r} - shorten the slug")
    return data


def summary(story: dict) -> str:
    """Inline caption for the sendVideo message (not the copyable caption file)."""
    return (f"{story['hook']['text']}\n"
            f"{story['category']} | {story['status']} | {story.get('source', 'club')}\n"
            f"TikTok: save this video, add a trending sound at ~20%, paste the "
            f"caption below. YouTube: tap approve.")


def deliver(day_dir: Path, story_id: str, run_id: str) -> None:
    day_dir = Path(day_dir)
    story = json.loads((day_dir / f"{story_id}.json").read_text(encoding="utf-8"))
    caption = (day_dir / f"{story_id}-caption.txt").read_text(encoding="utf-8")
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    keyboard = {"inline_keyboard": [[
        {"text": "✅ Post to YouTube",
         "callback_data": build_callback("ok", run_id, story_id)},
        {"text": "❌ Reject",
         "callback_data": build_callback("no", run_id, story_id)},
    ]]}
    with open(day_dir / f"{story_id}.mp4", "rb") as fh:
        msg = telegram_bot.call("sendVideo", files={"video": fh},
                                chat_id=chat_id, caption=summary(story),
                                reply_markup=json.dumps(keyboard))
    telegram_bot.call("sendMessage", chat_id=chat_id, text=caption,
                      reply_to_message_id=msg["message_id"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--day-dir", required=True)
    ap.add_argument("--ids", required=True, help="space-separated story ids")
    args = ap.parse_args()
    failed = []
    for sid in args.ids.split():
        try:
            deliver(Path(args.day_dir), sid, args.run_id)
            print(f"delivered {sid}")
        except Exception as exc:           # keep going - other stories must still arrive
            print(f"ERROR delivering {sid}: {exc}", file=sys.stderr)
            failed.append(sid)
    if failed:
        sys.exit(f"delivery failed for: {' '.join(failed)}")
