"""Story JSON loading and validation for the TikTok news pipeline."""
import datetime
import json
import re
from pathlib import Path

CATEGORIES = {"TRANSFER", "MATCHDAY", "CLUB", "ACADEMY"}
STATUSES = {"OFFICIAL", "CONFIRMED", "REPORTED", "RUMOUR"}
MOODS = {"celebrate", "tension", "roar", "react", "confident", "point"}
ATTRIBUTED = {"REPORTED", "RUMOUR"}  # must carry a source

REQUIRED = ("id", "date", "category", "status", "mood",
            "hook", "beats", "caption", "hashtags")


class StoryError(ValueError):
    pass


def _check_segment(seg, where):
    if not isinstance(seg, dict) or not isinstance(seg.get("text"), str) or not seg["text"]:
        raise StoryError(f"{where}: 'text' (non-empty string) is required")
    highlight = seg.get("highlight", "")
    if highlight and highlight not in seg["text"]:
        raise StoryError(f"{where}: highlight {highlight!r} not found in text {seg['text']!r}")
    if highlight and highlight.split() != []:
        words, hwords = seg["text"].split(), highlight.split()
        n = len(hwords)
        if not any(words[i:i + n] == hwords for i in range(len(words) - n + 1)):
            raise StoryError(f"{where}: highlight {highlight!r} must match whole words in {seg['text']!r}")


def validate(s: dict) -> dict:
    for field in REQUIRED:
        if field not in s:
            raise StoryError(f"missing required field: {field!r}")
    _date = s["date"]
    if not isinstance(_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", _date):
        raise StoryError(f"date must be YYYY-MM-DD, got {_date!r}")
    try:
        datetime.date.fromisoformat(_date)
    except (ValueError, TypeError):
        raise StoryError(f"date must be YYYY-MM-DD, got {_date!r}")
    if s["category"] not in CATEGORIES:
        raise StoryError(f"category must be one of {sorted(CATEGORIES)}, got {s['category']!r}")
    if s["status"] not in STATUSES:
        raise StoryError(f"status must be one of {sorted(STATUSES)}, got {s['status']!r}")
    if s["mood"] not in MOODS:
        raise StoryError(f"mood must be one of {sorted(MOODS)}, got {s['mood']!r}")
    if s["status"] in ATTRIBUTED and not s.get("source"):
        raise StoryError(f"status {s['status']} requires a non-empty 'source'")
    _check_segment(s["hook"], "hook")
    if not isinstance(s["beats"], list) or not 2 <= len(s["beats"]) <= 4:
        raise StoryError("beats must be a list of 2-4 entries")
    for i, beat in enumerate(s["beats"]):
        _check_segment(beat, f"beats[{i}]")
    if not isinstance(s["caption"], str) or not s["caption"]:
        raise StoryError("caption must be a non-empty string")
    if not isinstance(s["hashtags"], list) or not s["hashtags"]:
        raise StoryError("hashtags must be a non-empty list")
    if not all(isinstance(tag, str) and tag for tag in s["hashtags"]):
        raise StoryError("every hashtag must be a non-empty string")
    return s


def load(path) -> dict:
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))
