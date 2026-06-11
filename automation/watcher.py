"""Poll United news feeds, detect genuinely new stories, wake the editor.

Deterministic - no LLM. Runs on a GitHub Actions cron (.github/workflows/watcher.yml).
State lives in automation/state/seen.json (Actions cache, never committed).
"""
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = Path(__file__).resolve().parent / "state" / "seen.json"
SOURCES_PATH = ROOT / "tiktok" / "sources.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")
LONDON = ZoneInfo("Europe/London")
ACTIVE_HOURS = range(7, 22)      # 07:00-21:59 Europe/London
MAX_WAKES_PER_DAY = 3            # primary API-cost throttle (see spec)
PRUNE_DAYS = 7
JACCARD_DUPLICATE = 0.3          # similarity >= this counts as the same story
                                 # (0.3 not 0.5: rephrased headlines share only
                                 # ~40% of significant tokens; same-player but
                                 # different stories score <= 0.25)
ALERT_AFTER_FAILURES = 3         # consecutive all-feeds-down runs before alerting

STOPWORDS = {
    "the", "a", "an", "to", "of", "for", "in", "on", "at", "as", "and", "is",
    "are", "with", "after", "over", "amid", "his", "her", "he", "she", "it",
    "by", "from", "vs", "v", "man", "utd", "united", "manchester", "mufc",
    "fc", "news", "transfer", "transfers", "latest", "report", "reports",
    "reported", "update", "updates", "live", "why", "how", "what", "who",
    "new", "says", "could", "will", "be", "has", "have", "this", "that",
}


def tokens(title: str) -> frozenset:
    words = re.findall(r"[a-z0-9']+", title.lower())
    return frozenset(w for w in words if w not in STOPWORDS and len(w) > 1)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_new(sig: frozenset, seen: list) -> bool:
    return bool(sig) and all(jaccard(sig, s) < JACCARD_DUPLICATE for s in seen)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_titles(xml_text: str) -> list:
    """Titles from RSS <item> or Atom <entry>; channel/feed titles excluded."""
    out = []
    for el in ET.fromstring(xml_text).iter():
        if _local(el.tag) in ("item", "entry"):
            for child in el:
                if _local(child.tag) == "title" and child.text:
                    out.append(child.text.strip())
                    break
    return out


def watchable_feeds() -> list:
    """Feeds the watcher can poll: RSS/Atom only. HTML pages (Sky page,
    manutd.com) are skipped here - the editor still covers them."""
    cfg = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    out = []
    for f in cfg["feeds"]:
        if not f.get("enabled"):
            continue
        if f["type"] == "rss" or f["url"].endswith(".rss"):
            out.append({"name": f["name"], "url": f["url"]})
    return out


def fetch_feed(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def dispatch_editor(headlines: list) -> None:
    """Fire the editor workflow. MUST use a PAT - repository_dispatch events
    created with the default GITHUB_TOKEN do not trigger workflows."""
    repo = os.environ["GITHUB_REPOSITORY"]
    payload = json.dumps({
        "event_type": "editor-run",
        "client_payload": {"headlines": " | ".join(headlines[:10])},
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/dispatches",
        data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['REPO_DISPATCH_PAT']}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "red-mancunian-watcher",
            "X-GitHub-Api-Version": "2022-11-28",
        })
    urllib.request.urlopen(req, timeout=20)


def _alert_feeds_down(count: int) -> None:
    try:
        import telegram_bot
        telegram_bot.send_alert(
            f"Watcher: all feeds failed {count} runs in a row - check "
            "automation/watcher.py and sources.json.")
    except Exception as exc:                       # alerting must never crash the run
        print(f"alert failed: {exc}", file=sys.stderr)


def main(now=None) -> None:
    now = now or datetime.now(LONDON)
    if now.hour not in ACTIVE_HOURS:
        print("outside active hours - exiting")
        return

    headlines, failures = [], 0
    feeds = watchable_feeds()
    for feed in feeds:
        try:
            headlines.extend(parse_titles(fetch_feed(feed["url"])))
        except Exception as exc:
            failures += 1
            print(f"feed failed ({feed['name']}): {exc}", file=sys.stderr)

    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            STATE_PATH.unlink(missing_ok=True)   # re-seed on the next run
            print("corrupt state file - deleted, will re-seed", file=sys.stderr)
            return
    else:
        # Cache miss: seed everything as seen, trigger nothing (spec guardrail).
        state = {"stories": [], "wakes": {}, "failures": 0}
        for title in headlines:
            sig = tokens(title)
            if sig:
                state["stories"].append({"tokens": sorted(sig),
                                         "first_seen": now.isoformat()})
        _save(state)
        print(f"seeded state with {len(state['stories'])} stories - no dispatch")
        return

    if feeds and failures == len(feeds):
        state["failures"] = state.get("failures", 0) + 1
        if state["failures"] == ALERT_AFTER_FAILURES:
            _alert_feeds_down(state["failures"])
        _save(state)
        return
    state["failures"] = 0

    # prune fingerprints older than PRUNE_DAYS
    cutoff = now - timedelta(days=PRUNE_DAYS)
    state["stories"] = [s for s in state["stories"]
                        if datetime.fromisoformat(s["first_seen"]) >= cutoff]

    seen = [frozenset(s["tokens"]) for s in state["stories"]]
    fresh = []
    for title in headlines:
        sig = tokens(title)
        if is_new(sig, seen):
            fresh.append(title)
            seen.append(sig)
            state["stories"].append({"tokens": sorted(sig),
                                     "first_seen": now.isoformat()})

    day = now.date().isoformat()
    wakes = state["wakes"].get(day, 0)
    if fresh and wakes < MAX_WAKES_PER_DAY:
        print(f"dispatching editor for {len(fresh)} new headline(s)")
        dispatch_editor(fresh)
        state["wakes"] = {day: wakes + 1}          # only today's count is kept - the cap needs no history
    elif fresh:
        print(f"wake cap reached ({wakes}) - {len(fresh)} headline(s) marked seen only")
    else:
        print("nothing new")
    _save(state)


def _save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
