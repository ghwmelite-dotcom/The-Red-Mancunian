"""Delivered-video ledger: stops the same story being sent to Telegram twice.

tiktok/output/ is gitignored, so detect_new.py only dedupes within one editor
run. Across runs (2 daily baselines + breaking wakes + workflow retries) the
only guard was the editor happening not to re-pick a covered story. This
ledger is the deterministic backstop: delivery records every video it sends
(automation/delivered.json, committed by the editor workflow) and skips any
story whose id was already sent or whose hook+beats overlap a sent story.

Threshold rationale: a rewrite of the same news shares most significant
tokens (~0.5), a genuine follow-up (status moves up the ladder: talks ->
fee agreed -> confirmed) leads with new facts and scores ~0.2.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from watcher import jaccard, tokens

LEDGER_PATH = Path(__file__).resolve().parent / "delivered.json"
SIMILAR = 0.4
KEEP_DAYS = 14
LONDON = ZoneInfo("Europe/London")


def story_tokens(story: dict) -> frozenset:
    text = " ".join([story["hook"]["text"],
                     *(b["text"] for b in story.get("beats", []))])
    return tokens(text)


def load(now=None) -> list:
    """Ledger entries newer than KEEP_DAYS; missing/corrupt file -> empty."""
    now = now or datetime.now(LONDON)
    try:
        entries = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    cutoff = now - timedelta(days=KEEP_DAYS)
    return [e for e in entries
            if datetime.fromisoformat(e["sent_at"]) >= cutoff]


def duplicate_of(story_id: str, sig: frozenset, ledger: list):
    """Id of the already-sent entry this story duplicates, else None."""
    for e in ledger:
        if e["id"] == story_id:
            return e["id"]
        if jaccard(sig, frozenset(e["tokens"])) >= SIMILAR:
            return e["id"]
    return None


def record(ledger: list, story_id: str, sig: frozenset, now=None) -> None:
    """Append to the in-memory ledger AND persist immediately, so a crash
    later in the same run (or a workflow retry) cannot re-send this video."""
    now = now or datetime.now(LONDON)
    ledger.append({"id": story_id, "tokens": sorted(sig),
                   "sent_at": now.isoformat()})
    LEDGER_PATH.write_text(json.dumps(ledger, indent=1), encoding="utf-8")
