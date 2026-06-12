"""Upload a locally rendered -youtube.mp4 straight to YouTube.

Companion to send_local.py for videos that never went through the cloud
pipeline. Usage:
    python automation/upload_local.py <day_dir> <story_id> [--privacy unlisted]
Env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN,
     TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (link is sent to the chat).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telegram_bot
import youtube_upload

ap = argparse.ArgumentParser()
ap.add_argument("day_dir")
ap.add_argument("story_id")
ap.add_argument("--privacy", default="unlisted")
args = ap.parse_args()

day = Path(args.day_dir)
story = json.loads((day / f"{args.story_id}.json").read_text(encoding="utf-8"))
title = f"{story['hook']['text']} \U0001f534 #mufc"
description = (day / f"{args.story_id}-youtube-caption.txt").read_text(encoding="utf-8")

video_id = youtube_upload.upload(str(day / f"{args.story_id}-youtube.mp4"),
                                 title, description, args.privacy)
url = f"https://youtube.com/shorts/{video_id}"
telegram_bot.send_alert(f"✅ Live on YouTube ({args.privacy}): {url}")
print(url)
