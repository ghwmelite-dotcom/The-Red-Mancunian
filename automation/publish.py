"""Publish an approved story to YouTube and confirm in the Telegram thread.

Usage (publish workflow, after downloading the artifact to ./artifact):
    python automation/publish.py --root artifact --story-id <id> \
        --run-id <editor run id> --reply-to <telegram message id> --privacy unlisted

On failure, sends a Telegram alert with a Retry button (same callback as the
original approve button) and exits non-zero.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import telegram_bot
import youtube_upload

MAX_AGE_HOURS = 12


def locate(root: Path, story_id: str) -> dict:
    root = Path(root)
    mp4 = next(root.glob(f"**/{story_id}-youtube.mp4"))
    day = mp4.parent
    return {
        "mp4": mp4,
        "caption": (day / f"{story_id}-youtube-caption.txt").read_text(encoding="utf-8"),
        "story": json.loads((day / f"{story_id}.json").read_text(encoding="utf-8")),
        "meta": json.loads((day / "meta.json").read_text(encoding="utf-8")),
    }


def title_for(files: dict) -> str:
    return f"{files['story']['hook']['text']} \U0001f534 #mufc"


def run(root, story_id, reply_to, privacy, now=None) -> None:
    import os
    now = now or datetime.now(timezone.utc)
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    files = locate(root, story_id)

    if youtube_upload.is_stale(files["meta"]["rendered_at"], now, MAX_AGE_HOURS):
        telegram_bot.call(
            "sendMessage", chat_id=chat_id, reply_to_message_id=reply_to,
            text=(f"⚠️ Not uploaded: {story_id} is stale "
                  f"(rendered {files['meta']['rendered_at']}, limit "
                  f"{MAX_AGE_HOURS}h). Re-run the editor if still relevant."))
        return

    video_id = youtube_upload.upload(str(files["mp4"]), title_for(files),
                                     files["caption"], privacy)
    telegram_bot.call(
        "sendMessage", chat_id=chat_id, reply_to_message_id=reply_to,
        text=(f"✅ Live on YouTube ({privacy}): "
              f"https://youtube.com/shorts/{video_id}"))


def _alert_failure(story_id: str, run_id: str, error: Exception) -> None:
    import os
    keyboard = {"inline_keyboard": [[
        {"text": "\U0001f501 Retry", "callback_data": f"ok:{run_id}:{story_id}"}]]}
    telegram_bot.call("sendMessage", chat_id=os.environ["TELEGRAM_CHAT_ID"],
                      text=f"❌ YouTube upload failed for {story_id}: {error}",
                      reply_markup=json.dumps(keyboard))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--story-id", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--reply-to", required=True)
    ap.add_argument("--privacy", default="unlisted")
    args = ap.parse_args()
    try:
        run(Path(args.root), args.story_id, args.reply_to, args.privacy)
    except Exception as exc:
        _alert_failure(args.story_id, args.run_id, exc)
        sys.exit(f"publish failed: {exc}")
