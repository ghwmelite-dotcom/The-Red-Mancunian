# Breaking-News Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cloud pipeline that watches Man Utd news feeds every 30 minutes, generates TikTok + YouTube Shorts videos via the existing `/mufc-update` editorial logic on GitHub Actions, delivers them to Telegram for one-tap approval, and auto-posts approved videos to YouTube.

**Architecture:** A deterministic Python watcher (cron, no LLM) fingerprints headlines and fires a `repository_dispatch` when a genuinely new story appears. The editor workflow runs `claude -p` with an API key, renders with the existing `tiktok/render.py`, uploads videos as a workflow artifact, and sends them to a Telegram bot with inline buttons. A Cloudflare Worker receives the button webhook and dispatches the publish workflow, which uploads the `-youtube.mp4` via the YouTube Data API. TikTok posting stays manual from the Telegram message (preserves trending sounds).

**Tech Stack:** Python 3.12 (stdlib + requests + Pillow), GitHub Actions, Telegram Bot API, Cloudflare Workers (plain JS, wrangler), YouTube Data API v3, `@anthropic-ai/claude-code` CLI.

**Spec:** `docs/superpowers/specs/2026-06-11-breaking-news-automation-design.md`

**Key facts an engineer needs (verified against this repo):**
- Brand assets (fonts, character art, logo) are vendored at `branding/` — nothing extra to install for rendering beyond Pillow + ffmpeg.
- `tiktok/render.py` is the render CLI; `tiktok/video.py` shells out to `ffmpeg` directly (no moviepy).
- Existing tests: `pytest tiktok/tests` (conftest inserts the `tiktok/` dir on `sys.path`).
- The editorial brain is `.claude/commands/mufc-update.md`; the current local automation prompt lives in `tiktok/run-daily.ps1` lines 44–46 — the cloud editor reuses that exact prompt text.
- `tiktok/output/` is gitignored; story JSONs in `tiktok/stories/` are committed.
- **Gotcha:** `repository_dispatch` events created with the default `GITHUB_TOKEN` do NOT trigger workflows. Both the watcher and the Worker must use a fine-grained PAT (secret `REPO_DISPATCH_PAT` in the repo, `GH_DISPATCH_PAT` in the Worker) with **Contents: read+write** on this repo.
- Telegram `callback_data` is limited to **64 bytes** — callbacks are `ok:<run_id>:<story_id>`; delivery refuses longer ids with a clear error.

---

### Task 1: Repo on GitHub + automation skeleton

**Files:**
- Create: `requirements.txt`
- Create: `automation/__init__.py` (empty)
- Create: `automation/tests/__init__.py` (empty)
- Create: `automation/tests/conftest.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create requirements.txt**

```
Pillow>=10.0
requests>=2.31
pytest>=8.0
```

- [ ] **Step 2: Create package markers and conftest**

`automation/__init__.py` and `automation/tests/__init__.py` are empty files.

`automation/tests/conftest.py`:

```python
"""Make the automation modules importable from the tests directory."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 3: Ignore watcher state**

Append to `.gitignore`:

```
automation/state/
```

- [ ] **Step 4: Push the repo to GitHub (private)**

```bash
gh repo create The-Red-Mancunian --private --source . --push
```

Expected: repo created under the logged-in account, `master` pushed. Verify with `gh repo view --json visibility` → `"visibility": "PRIVATE"`. (If `gh` is not authenticated, run `gh auth login` first — interactive, so ask the user to run it with `! gh auth login` if needed.)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt automation/ .gitignore
git commit -m "chore(automation): skeleton, requirements, state ignore"
git push
```

---

### Task 2: Watcher pure logic — fingerprints, similarity, feed parsing

**Files:**
- Create: `automation/watcher.py`
- Test: `automation/tests/test_watcher.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_watcher.py`:

```python
import watcher


def test_tokens_strips_stopwords_and_normalizes():
    sig = watcher.tokens("Man Utd backing away from the Anderson chase!")
    assert sig == frozenset({"backing", "away", "anderson", "chase"})


def test_tokens_drops_single_letters():
    assert "s" not in watcher.tokens("United's plan")


def test_jaccard():
    a, b = frozenset({"x", "y"}), frozenset({"y", "z"})
    assert watcher.jaccard(a, b) == 1 / 3
    assert watcher.jaccard(a, frozenset()) == 0.0


def test_is_new_rejects_near_duplicates():
    seen = [watcher.tokens("Rashford returns to United after Barcelona decision")]
    assert not watcher.is_new(
        watcher.tokens("Marcus Rashford set for United return - Barcelona decision made"),
        seen,
    )
    assert watcher.is_new(watcher.tokens("United agree fee for Lewis Hall"), seen)


def test_is_new_ignores_empty_signatures():
    assert not watcher.is_new(frozenset(), [])


RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Feed</title>
<item><title>Story one</title></item>
<item><title>Story two</title></item>
</channel></rss>"""

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>r/reddevils</title>
<entry><title>Atom story</title></entry>
</feed>"""


def test_parse_titles_rss_skips_channel_title():
    assert watcher.parse_titles(RSS) == ["Story one", "Story two"]


def test_parse_titles_atom():
    assert watcher.parse_titles(ATOM) == ["Atom story"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_watcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'watcher'`

- [ ] **Step 3: Implement the pure logic**

`automation/watcher.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_watcher.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add automation/watcher.py automation/tests/test_watcher.py
git commit -m "feat(automation): watcher fingerprinting and feed parsing"
```

---

### Task 3: Watcher orchestration — state, rate limit, seeding, main()

**Files:**
- Modify: `automation/watcher.py` (append)
- Test: `automation/tests/test_watcher.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `automation/tests/test_watcher.py`:

```python
import json
from datetime import datetime
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
NOON = datetime(2026, 6, 11, 12, 0, tzinfo=LONDON)
NIGHT = datetime(2026, 6, 11, 23, 0, tzinfo=LONDON)


def run_main(tmp_path, monkeypatch, now, titles, state=None):
    """Drive watcher.main with injected IO; returns (dispatched, state_dict)."""
    state_path = tmp_path / "seen.json"
    if state is not None:
        state_path.write_text(json.dumps(state))
    monkeypatch.setattr(watcher, "STATE_PATH", state_path)
    monkeypatch.setattr(watcher, "watchable_feeds",
                        lambda: [{"name": "stub", "url": "http://stub"}])
    dispatched = []
    monkeypatch.setattr(watcher, "dispatch_editor", dispatched.append)
    monkeypatch.setattr(watcher, "fetch_feed", lambda url: _rss(titles))
    watcher.main(now=now)
    return dispatched, json.loads(state_path.read_text())


def _rss(titles):
    items = "".join(f"<item><title>{t}</title></item>" for t in titles)
    return f"<rss><channel><title>F</title>{items}</channel></rss>"


def test_missing_state_seeds_without_dispatch(tmp_path, monkeypatch):
    dispatched, state = run_main(tmp_path, monkeypatch, NOON,
                                 ["United agree Hall fee"])
    assert dispatched == []
    assert len(state["stories"]) == 1


def test_new_story_dispatches_and_counts_wake(tmp_path, monkeypatch):
    seeded = {"stories": [], "wakes": {}, "failures": 0}
    dispatched, state = run_main(tmp_path, monkeypatch, NOON,
                                 ["United agree Hall fee"], state=seeded)
    assert dispatched == [["United agree Hall fee"]]
    assert state["wakes"]["2026-06-11"] == 1


def test_known_story_does_not_dispatch(tmp_path, monkeypatch):
    seeded = {"stories": [{"tokens": sorted(watcher.tokens("United agree Hall fee")),
                           "first_seen": "2026-06-11T08:00:00+01:00"}],
              "wakes": {}, "failures": 0}
    dispatched, _ = run_main(tmp_path, monkeypatch, NOON,
                             ["United agree fee for Hall"], state=seeded)
    assert dispatched == []


def test_wake_cap_blocks_dispatch_but_still_marks_seen(tmp_path, monkeypatch):
    seeded = {"stories": [], "wakes": {"2026-06-11": 3}, "failures": 0}
    dispatched, state = run_main(tmp_path, monkeypatch, NOON,
                                 ["United agree Hall fee"], state=seeded)
    assert dispatched == []
    assert len(state["stories"]) == 1          # no re-trigger next run


def test_outside_active_hours_is_a_noop(tmp_path, monkeypatch):
    seeded = {"stories": [], "wakes": {}, "failures": 0}
    dispatched, state = run_main(tmp_path, monkeypatch, NIGHT,
                                 ["United agree Hall fee"], state=seeded)
    assert dispatched == []
    assert state["stories"] == []


def test_prune_drops_old_fingerprints(tmp_path, monkeypatch):
    seeded = {"stories": [{"tokens": ["ancient", "story"],
                           "first_seen": "2026-06-01T08:00:00+01:00"}],
              "wakes": {}, "failures": 0}
    _, state = run_main(tmp_path, monkeypatch, NOON, [], state=seeded)
    assert state["stories"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_watcher.py -v`
Expected: new tests FAIL — `AttributeError: module 'watcher' has no attribute 'main'` (the 7 Task-2 tests still pass)

- [ ] **Step 3: Implement orchestration**

Append to `automation/watcher.py`:

```python
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
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
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
    cutoff = (now - timedelta(days=PRUNE_DAYS)).isoformat()
    state["stories"] = [s for s in state["stories"] if s["first_seen"] >= cutoff]

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
        state["wakes"] = {day: wakes + 1}          # old days drop off naturally
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
```

- [ ] **Step 4: Run all watcher tests**

Run: `python -m pytest automation/tests/test_watcher.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add automation/watcher.py automation/tests/test_watcher.py
git commit -m "feat(automation): watcher orchestration - state, wake cap, seeding"
```

---

### Task 4: Telegram module — API wrapper + alert CLI

**Files:**
- Create: `automation/telegram_bot.py`
- Test: `automation/tests/test_telegram_bot.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_telegram_bot.py`:

```python
import telegram_bot


def test_call_posts_to_bot_api(monkeypatch):
    calls = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": {"message_id": 7}}

    def fake_post(url, data=None, files=None, timeout=None):
        calls.update(url=url, data=data, files=files)
        return FakeResp()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setattr(telegram_bot.requests, "post", fake_post)
    result = telegram_bot.call("sendMessage", chat_id="42", text="hi")
    assert calls["url"] == "https://api.telegram.org/botTOK/sendMessage"
    assert calls["data"] == {"chat_id": "42", "text": "hi"}
    assert result == {"message_id": 7}


def test_send_alert_uses_chat_id_env(monkeypatch):
    sent = {}
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(telegram_bot, "call",
                        lambda method, **p: sent.update(method=method, **p))
    telegram_bot.send_alert("boom")
    assert sent == {"method": "sendMessage", "chat_id": "42", "text": "boom"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_telegram_bot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'telegram_bot'`

- [ ] **Step 3: Implement**

`automation/telegram_bot.py`:

```python
"""Thin Telegram Bot API wrapper + alert CLI.

Usage from workflows:  python automation/telegram_bot.py alert "message text"
Env: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import os
import sys

import requests


def call(method: str, files=None, **params) -> dict:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_telegram_bot.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add automation/telegram_bot.py automation/tests/test_telegram_bot.py
git commit -m "feat(automation): telegram bot wrapper and alert CLI"
```

---

### Task 5: Delivery — story message with approve/reject buttons

**Files:**
- Create: `automation/delivery.py`
- Test: `automation/tests/test_delivery.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_delivery.py`:

```python
import json

import pytest

import delivery


def test_build_callback_format():
    assert delivery.build_callback("ok", "1234", "2026-06-11-hall") == \
        "ok:1234:2026-06-11-hall"


def test_build_callback_rejects_over_64_bytes():
    with pytest.raises(ValueError):
        delivery.build_callback("ok", "16234567890", "x" * 60)


def test_summary_lines(tmp_path):
    s = {"hook": {"text": "UNITED WANT A NEW LEFT-BACK"},
         "category": "TRANSFER", "status": "REPORTED", "source": "Sky Sports"}
    text = delivery.summary(s)
    assert "UNITED WANT A NEW LEFT-BACK" in text
    assert "TRANSFER" in text and "REPORTED" in text and "Sky Sports" in text


def test_deliver_sends_video_then_caption(tmp_path, monkeypatch):
    day = tmp_path
    (day / "2026-06-11-hall.mp4").write_bytes(b"vid")
    (day / "2026-06-11-hall-caption.txt").write_text("caption text", encoding="utf-8")
    (day / "2026-06-11-hall.json").write_text(json.dumps(
        {"hook": {"text": "HOOK"}, "category": "TRANSFER",
         "status": "REPORTED", "source": "Sky Sports"}), encoding="utf-8")

    sent = []
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(delivery.telegram_bot, "call",
                        lambda method, files=None, **p:
                        (sent.append((method, p)), {"message_id": 9})[1])
    delivery.deliver(day, "2026-06-11-hall", "777")

    assert sent[0][0] == "sendVideo"
    keyboard = json.loads(sent[0][1]["reply_markup"])
    assert keyboard["inline_keyboard"][0][0]["callback_data"] == "ok:777:2026-06-11-hall"
    assert sent[1] == ("sendMessage",
                       {"chat_id": "42", "text": "caption text",
                        "reply_to_message_id": 9})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_delivery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'delivery'`

- [ ] **Step 3: Implement**

`automation/delivery.py`:

```python
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
from pathlib import Path

import telegram_bot


def build_callback(action: str, run_id: str, story_id: str) -> str:
    data = f"{action}:{run_id}:{story_id}"
    if len(data.encode()) > 64:
        raise ValueError(
            f"callback_data over Telegram's 64-byte limit: {data!r} - shorten the slug")
    return data


def summary(story: dict) -> str:
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
    for sid in args.ids.split():
        deliver(Path(args.day_dir), sid, args.run_id)
        print(f"delivered {sid}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_delivery.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add automation/delivery.py automation/tests/test_delivery.py
git commit -m "feat(automation): telegram delivery with approve/reject buttons"
```

---

### Task 6: detect_new.py — diff renders, write artifact meta

**Files:**
- Create: `automation/detect_new.py`
- Test: `automation/tests/test_detect_new.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_detect_new.py`:

```python
import json

import detect_new


def test_new_ids_excludes_youtube_variants_and_known(tmp_path):
    for name in ("a.mp4", "a-youtube.mp4", "b.mp4", "b-youtube.mp4"):
        (tmp_path / name).write_bytes(b"")
    assert detect_new.new_ids(tmp_path, before={"a.mp4", "a-youtube.mp4"}) == ["b"]


def test_write_meta(tmp_path):
    detect_new.write_meta(tmp_path, run_id="99", ids=["b"],
                          rendered_at="2026-06-11T18:00:00+01:00")
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta == {"run_id": "99", "story_ids": ["b"],
                    "rendered_at": "2026-06-11T18:00:00+01:00"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_detect_new.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`automation/detect_new.py`:

```python
"""Diff the day's output dir against a pre-run snapshot; emit new story ids.

Usage (editor workflow):
    ls <day_dir>/*.mp4 > /tmp/before.txt   (before the editor runs; missing dir ok)
    python automation/detect_new.py /tmp/before.txt <day_dir>

Writes meta.json (run_id, story_ids, rendered_at) into the day dir for the
publisher's staleness check, and appends new_ids=<space separated> to
$GITHUB_OUTPUT.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def new_ids(day_dir: Path, before: set) -> list:
    after = {p.name for p in Path(day_dir).glob("*.mp4")}
    fresh = sorted(after - before)
    return [n[:-4] for n in fresh if not n.endswith("-youtube.mp4")]


def write_meta(day_dir: Path, run_id: str, ids: list, rendered_at: str) -> None:
    (Path(day_dir) / "meta.json").write_text(
        json.dumps({"run_id": run_id, "story_ids": ids,
                    "rendered_at": rendered_at}), encoding="utf-8")


if __name__ == "__main__":
    before_file, day_dir = sys.argv[1], Path(sys.argv[2])
    before = {Path(line).name for line in
              Path(before_file).read_text().splitlines() if line.strip()}
    day_dir.mkdir(parents=True, exist_ok=True)
    ids = new_ids(day_dir, before)
    write_meta(day_dir, os.environ.get("GITHUB_RUN_ID", "local"), ids,
               datetime.now(ZoneInfo("Europe/London")).isoformat())
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"new_ids={' '.join(ids)}\n")
    print(f"new story ids: {ids or 'none'}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_detect_new.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add automation/detect_new.py automation/tests/test_detect_new.py
git commit -m "feat(automation): detect newly rendered stories, write artifact meta"
```

---

### Task 7: YouTube upload module

**Files:**
- Create: `automation/youtube_upload.py`
- Test: `automation/tests/test_youtube_upload.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_youtube_upload.py`:

```python
from datetime import datetime, timezone

import youtube_upload


def test_is_stale():
    now = datetime(2026, 6, 12, 9, 0, tzinfo=timezone.utc)
    assert youtube_upload.is_stale("2026-06-11T18:00:00+01:00", now, max_hours=12)
    assert not youtube_upload.is_stale("2026-06-12T08:00:00+01:00", now, max_hours=12)


def test_build_metadata_truncates_title_and_sets_privacy():
    meta = youtube_upload.build_metadata("X" * 120, "desc", "unlisted")
    assert len(meta["snippet"]["title"]) == 100
    assert meta["snippet"]["categoryId"] == "17"          # Sports
    assert meta["status"] == {"privacyStatus": "unlisted",
                              "selfDeclaredMadeForKids": False}


def test_get_access_token(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"access_token": "AT"}

    posted = {}

    def fake_post(url, data=None, timeout=None):
        posted.update(url=url, data=data)
        return FakeResp()

    for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"):
        monkeypatch.setenv(k, k.lower())
    monkeypatch.setattr(youtube_upload.requests, "post", fake_post)
    assert youtube_upload.get_access_token() == "AT"
    assert posted["url"] == "https://oauth2.googleapis.com/token"
    assert posted["data"]["grant_type"] == "refresh_token"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_youtube_upload.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`automation/youtube_upload.py`:

```python
"""Upload a Short to YouTube via resumable upload (no Google SDK needed).

Env: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
Quota: one upload costs 1600 of the 10,000 daily units (= 6 uploads/day max).
"""
import os
from datetime import datetime

import requests

UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")


def is_stale(rendered_at_iso: str, now: datetime, max_hours: int = 12) -> bool:
    rendered = datetime.fromisoformat(rendered_at_iso)
    return (now - rendered).total_seconds() > max_hours * 3600


def build_metadata(title: str, description: str, privacy: str) -> dict:
    return {
        "snippet": {"title": title[:100], "description": description,
                    "categoryId": "17"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }


def get_access_token() -> str:
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def upload(mp4_path: str, title: str, description: str, privacy: str) -> str:
    """Returns the YouTube video id."""
    token = get_access_token()
    size = os.path.getsize(mp4_path)
    start = requests.post(UPLOAD_URL, json=build_metadata(title, description, privacy),
                          headers={"Authorization": f"Bearer {token}",
                                   "X-Upload-Content-Type": "video/mp4",
                                   "X-Upload-Content-Length": str(size)},
                          timeout=60)
    start.raise_for_status()
    session_url = start.headers["Location"]
    with open(mp4_path, "rb") as fh:
        done = requests.put(session_url, data=fh,
                            headers={"Content-Type": "video/mp4",
                                     "Content-Length": str(size)},
                            timeout=600)
    done.raise_for_status()
    return done.json()["id"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_youtube_upload.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add automation/youtube_upload.py automation/tests/test_youtube_upload.py
git commit -m "feat(automation): youtube resumable upload module"
```

---

### Task 8: publish.py — artifact → YouTube → Telegram reply

**Files:**
- Create: `automation/publish.py`
- Test: `automation/tests/test_publish.py`

- [ ] **Step 1: Write the failing tests**

`automation/tests/test_publish.py`:

```python
import json
from datetime import datetime, timezone

import publish


def make_artifact(tmp_path, story_id="2026-06-11-hall",
                  rendered_at="2026-06-11T18:00:00+01:00"):
    day = tmp_path / "2026-06-11"
    day.mkdir()
    (day / f"{story_id}-youtube.mp4").write_bytes(b"vid")
    (day / f"{story_id}-youtube-caption.txt").write_text("desc", encoding="utf-8")
    (day / f"{story_id}.json").write_text(json.dumps(
        {"hook": {"text": "UNITED WANT A NEW LEFT-BACK"}}), encoding="utf-8")
    (day / "meta.json").write_text(json.dumps(
        {"run_id": "777", "story_ids": [story_id],
         "rendered_at": rendered_at}), encoding="utf-8")
    return tmp_path


def test_locate_finds_files(tmp_path):
    root = make_artifact(tmp_path)
    files = publish.locate(root, "2026-06-11-hall")
    assert files["mp4"].name == "2026-06-11-hall-youtube.mp4"
    assert files["meta"]["run_id"] == "777"


def test_title_format(tmp_path):
    root = make_artifact(tmp_path)
    files = publish.locate(root, "2026-06-11-hall")
    assert publish.title_for(files) == "UNITED WANT A NEW LEFT-BACK \U0001f534 #mufc"


def test_run_refuses_stale_artifact(tmp_path, monkeypatch):
    root = make_artifact(tmp_path, rendered_at="2026-06-10T06:00:00+01:00")
    sent = []
    monkeypatch.setattr(publish.telegram_bot, "call",
                        lambda method, **p: sent.append((method, p)) or {})
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    uploaded = []
    monkeypatch.setattr(publish.youtube_upload, "upload",
                        lambda *a, **k: uploaded.append(a) or "vid123")
    now = datetime(2026, 6, 11, 23, 0, tzinfo=timezone.utc)
    publish.run(root, "2026-06-11-hall", reply_to="9", privacy="unlisted", now=now)
    assert uploaded == []
    assert "stale" in sent[0][1]["text"].lower()


def test_run_uploads_and_replies(tmp_path, monkeypatch):
    root = make_artifact(tmp_path)
    sent = []
    monkeypatch.setattr(publish.telegram_bot, "call",
                        lambda method, **p: sent.append((method, p)) or {})
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    monkeypatch.setattr(publish.youtube_upload, "upload",
                        lambda *a, **k: "vid123")
    now = datetime(2026, 6, 11, 19, 0, tzinfo=timezone.utc)
    publish.run(root, "2026-06-11-hall", reply_to="9", privacy="unlisted", now=now)
    assert "youtube.com/shorts/vid123" in sent[0][1]["text"]
    assert sent[0][1]["reply_to_message_id"] == "9"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest automation/tests/test_publish.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`automation/publish.py`:

```python
"""Publish an approved story to YouTube and confirm in the Telegram thread.

Usage (publish workflow, after downloading the artifact to ./artifact):
    python automation/publish.py --root artifact --story-id <id> \
        --reply-to <telegram message id> --privacy unlisted

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest automation/tests/test_publish.py -v`
Expected: 4 passed

- [ ] **Step 5: Run the FULL suite (both test trees)**

Run: `python -m pytest tiktok/tests automation/tests -v`
Expected: all pass — the automation work must not break the render pipeline tests.

- [ ] **Step 6: Commit**

```bash
git add automation/publish.py automation/tests/test_publish.py
git commit -m "feat(automation): publish module - staleness guard, upload, confirm"
```

---

### Task 9: One-time Google OAuth helper

**Files:**
- Create: `automation/get_refresh_token.py`

No unit tests — this is an interactive one-time tool, verified by running it during setup (Task 12).

- [ ] **Step 1: Implement**

`automation/get_refresh_token.py`:

```python
"""One-time: obtain a Google OAuth refresh token for YouTube uploads.

Prereqs (see automation/SETUP.md): a Google Cloud project with the YouTube
Data API v3 enabled and an OAuth client of type "Desktop app".

Run LOCALLY (it opens a browser):
    set GOOGLE_CLIENT_ID=...        (PowerShell: $env:GOOGLE_CLIENT_ID="...")
    set GOOGLE_CLIENT_SECRET=...
    python automation/get_refresh_token.py

Prints the refresh token - store it as the GOOGLE_REFRESH_TOKEN repo secret.
"""
import http.server
import os
import urllib.parse
import webbrowser

import requests

PORT = 8765
REDIRECT = f"http://localhost:{PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main():
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?" +
                urllib.parse.urlencode({
                    "client_id": client_id, "redirect_uri": REDIRECT,
                    "response_type": "code", "scope": SCOPE,
                    "access_type": "offline", "prompt": "consent"}))
    print("Opening browser - sign in as the channel owner (@theredmancunianway)...")
    webbrowser.open(auth_url)

    code_holder = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            code_holder["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Done - return to the terminal.")

        def log_message(self, *a):
            pass

    with http.server.HTTPServer(("localhost", PORT), Handler) as srv:
        srv.handle_request()

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "code": code_holder["code"], "redirect_uri": REDIRECT,
        "grant_type": "authorization_code"}, timeout=30)
    resp.raise_for_status()
    print("\nGOOGLE_REFRESH_TOKEN =", resp.json()["refresh_token"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-check it imports**

Run: `python -c "import ast; ast.parse(open('automation/get_refresh_token.py').read())"`
Expected: no output (parses cleanly). Real verification happens in Task 12.

- [ ] **Step 3: Commit**

```bash
git add automation/get_refresh_token.py
git commit -m "feat(automation): one-time google oauth refresh-token helper"
```

---

### Task 10: GitHub Actions workflows (watcher, editor, publish)

**Files:**
- Create: `.github/workflows/watcher.yml`
- Create: `.github/workflows/editor.yml`
- Create: `.github/workflows/publish-youtube.yml`
- Create: `automation/run_editor.sh`

- [ ] **Step 1: Watcher workflow**

`.github/workflows/watcher.yml`:

```yaml
name: news-watcher
on:
  schedule:
    - cron: "*/30 6-21 * * *"   # UTC; watcher.py re-gates to 07:00-22:00 Europe/London
  workflow_dispatch: {}
permissions:
  contents: read
concurrency:
  group: news-watcher
jobs:
  watch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests
      - name: Restore watcher state
        uses: actions/cache/restore@v4
        with:
          path: automation/state
          key: watcher-state-${{ github.run_id }}
          restore-keys: watcher-state-
      - name: Run watcher
        env:
          REPO_DISPATCH_PAT: ${{ secrets.REPO_DISPATCH_PAT }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python automation/watcher.py
      - name: Save watcher state
        if: always()
        uses: actions/cache/save@v4
        with:
          path: automation/state
          key: watcher-state-${{ github.run_id }}
```

- [ ] **Step 2: Editor prompt script**

`automation/run_editor.sh` (the baseline prompt text is copied verbatim from `tiktok/run-daily.ps1`):

```bash
#!/usr/bin/env bash
# Build the /mufc-update prompt for unattended cloud runs and invoke claude.
# Env: EDITOR_MODE=baseline|breaking, WATCHER_HEADLINES (breaking only),
#      ANTHROPIC_API_KEY.
set -euo pipefail

PROMPT="/mufc-update UNATTENDED RUN: never wait for user input. On slow days do \
not render evergreen content - write the recommendation in your summary \
instead. Render both platform versions of any selected story."

if [ "${EDITOR_MODE:-baseline}" = "breaking" ]; then
  PROMPT="$PROMPT BREAKING MODE: the news watcher triggered this run for these \
new headlines - verify their dates and prioritise them, applying the playbook \
surge bar (score >= 6): ${WATCHER_HEADLINES:-unknown}"
fi

claude -p "$PROMPT" --model claude-sonnet-4-6 \
  --allowedTools "WebFetch,WebSearch,Read,Glob,Grep,Write,Bash(python tiktok/render.py:*),Bash(curl:*)"
```

- [ ] **Step 3: Editor workflow**

`.github/workflows/editor.yml`:

```yaml
name: editor
on:
  repository_dispatch:
    types: [editor-run]
  schedule:
    - cron: "0 8 * * *"   # 09:00 UK in summer (08:00 in winter - acceptable drift)
  workflow_dispatch:
    inputs:
      dry_run:
        description: "Render but skip Telegram delivery"
        type: boolean
        default: false
permissions:
  contents: write
concurrency:
  group: editor
jobs:
  edit:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - name: Install dependencies
        run: |
          sudo apt-get update -q && sudo apt-get install -y -q ffmpeg
          pip install -r requirements.txt
          npm install -g @anthropic-ai/claude-code
      - name: Snapshot existing output
        id: snapshot
        run: |
          DAY=$(TZ=Europe/London date +%F)
          echo "day=$DAY" >> "$GITHUB_OUTPUT"
          ls "tiktok/output/$DAY/"*.mp4 > /tmp/before.txt 2>/dev/null || : > /tmp/before.txt
      - name: Run editor
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          EDITOR_MODE: ${{ github.event_name == 'repository_dispatch' && 'breaking' || 'baseline' }}
          WATCHER_HEADLINES: ${{ github.event.client_payload.headlines }}
        run: bash automation/run_editor.sh
      - name: Commit story JSONs
        run: |
          git config user.name "red-mancunian-bot"
          git config user.email "red-mancunian-bot@users.noreply.github.com"
          git add tiktok/stories/*.json
          git diff --cached --quiet || git commit -m "content: automated run ${{ steps.snapshot.outputs.day }} (${{ github.run_id }})"
          git push
      - name: Detect new videos
        id: detect
        run: python automation/detect_new.py /tmp/before.txt "tiktok/output/${{ steps.snapshot.outputs.day }}"
      - name: Upload videos artifact
        if: steps.detect.outputs.new_ids != ''
        uses: actions/upload-artifact@v4
        with:
          name: videos-${{ github.run_id }}
          path: tiktok/output/
          retention-days: 7
      - name: Deliver to Telegram
        if: steps.detect.outputs.new_ids != '' && github.event.inputs.dry_run != 'true'
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python automation/delivery.py --run-id "${{ github.run_id }}" \
            --day-dir "tiktok/output/${{ steps.snapshot.outputs.day }}" \
            --ids "${{ steps.detect.outputs.new_ids }}"
      - name: Alert on failure
        if: failure()
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python automation/telegram_bot.py alert \
            "Editor run failed: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
```

- [ ] **Step 4: Publish workflow**

`.github/workflows/publish-youtube.yml`:

```yaml
name: publish-youtube
on:
  repository_dispatch:
    types: [publish-youtube]
permissions:
  contents: read
  actions: read
jobs:
  publish:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests
      - name: Download videos artifact
        uses: actions/download-artifact@v4
        with:
          name: videos-${{ github.event.client_payload.run_id }}
          run-id: ${{ github.event.client_payload.run_id }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          path: artifact
      - name: Publish
        env:
          GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET: ${{ secrets.GOOGLE_CLIENT_SECRET }}
          GOOGLE_REFRESH_TOKEN: ${{ secrets.GOOGLE_REFRESH_TOKEN }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python automation/publish.py --root artifact \
            --story-id "${{ github.event.client_payload.story_id }}" \
            --run-id "${{ github.event.client_payload.run_id }}" \
            --reply-to "${{ github.event.client_payload.message_id }}" \
            --privacy "${{ vars.YOUTUBE_PRIVACY || 'unlisted' }}"
```

- [ ] **Step 5: Validate YAML locally**

```bash
python - <<'EOF'
import yaml, glob
for f in glob.glob(".github/workflows/*.yml"):
    yaml.safe_load(open(f)); print("ok", f)
EOF
```

Expected: `ok` ×3. (If PyYAML is missing: `pip install pyyaml`.)

- [ ] **Step 6: Commit and push**

```bash
git add .github/workflows automation/run_editor.sh
git commit -m "feat(automation): watcher, editor, publish workflows"
git push
```

- [ ] **Step 7: Verify the watcher runs on GitHub**

```bash
gh workflow run news-watcher && sleep 60 && gh run list --workflow news-watcher --limit 1
```

Expected: a completed run. Its log shows "seeded state with N stories - no dispatch" on first run (no secrets needed for seeding). Subsequent manual run shows "nothing new".

---

### Task 11: Cloudflare Worker — approval relay

**Files:**
- Create: `automation/worker/wrangler.toml`
- Create: `automation/worker/src/index.js`

- [ ] **Step 1: wrangler.toml**

`automation/worker/wrangler.toml`:

```toml
name = "red-mancunian-approval"
main = "src/index.js"
compatibility_date = "2026-06-01"

[vars]
GH_REPO = "OWNER/The-Red-Mancunian"   # set to the real owner/repo at deploy time
```

- [ ] **Step 2: Worker code**

`automation/worker/src/index.js`:

```js
// Telegram approval relay: webhook -> verify -> repository_dispatch.
// Secrets (wrangler secret put): TELEGRAM_WEBHOOK_SECRET, TELEGRAM_BOT_TOKEN,
// GH_DISPATCH_PAT (fine-grained, this repo only, Contents: read+write).

async function tg(env, method, body) {
  return fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') return new Response('ok');
    if (request.headers.get('x-telegram-bot-api-secret-token') !==
        env.TELEGRAM_WEBHOOK_SECRET) {
      return new Response('forbidden', { status: 403 });
    }

    const update = await request.json();
    const cb = update.callback_query;
    if (!cb || !cb.data) return new Response('ok');

    // callback_data = "<action>:<run_id>:<story_id>"
    const [action, runId, ...rest] = cb.data.split(':');
    const storyId = rest.join(':');

    if (action === 'ok') {
      const r = await fetch(`https://api.github.com/repos/${env.GH_REPO}/dispatches`, {
        method: 'POST',
        headers: {
          authorization: `Bearer ${env.GH_DISPATCH_PAT}`,
          accept: 'application/vnd.github+json',
          'user-agent': 'red-mancunian-approval',
          'x-github-api-version': '2022-11-28',
        },
        body: JSON.stringify({
          event_type: 'publish-youtube',
          client_payload: {
            run_id: runId,
            story_id: storyId,
            chat_id: cb.message.chat.id,
            message_id: cb.message.message_id,
          },
        }),
      });
      await tg(env, 'answerCallbackQuery', {
        callback_query_id: cb.id,
        text: r.status === 204 ? 'Queued for YouTube ✅' : `Dispatch failed (${r.status})`,
      });
    } else if (action === 'no') {
      await tg(env, 'answerCallbackQuery', { callback_query_id: cb.id, text: 'Rejected' });
      await tg(env, 'editMessageCaption', {
        chat_id: cb.message.chat.id,
        message_id: cb.message.message_id,
        caption: `${cb.message.caption || ''}\n\n❌ REJECTED`,
      });
    }
    return new Response('ok');
  },
};
```

- [ ] **Step 3: Commit**

```bash
git add automation/worker
git commit -m "feat(automation): cloudflare worker approval relay"
git push
```

Deploy + webhook registration happen in Task 12 (they need the bot token first).

---

### Task 12: Setup runbook + PLAYBOOK update + cutover

**Files:**
- Create: `automation/SETUP.md`
- Modify: `tiktok/PLAYBOOK.md` (the "Automation (scheduled runs)" section)

- [ ] **Step 1: Write the runbook**

`automation/SETUP.md`:

```markdown
# One-time setup — breaking-news pipeline

Work through these in order. Everything here is manual/one-time; daily
operation needs none of it.

## 1. Telegram bot
1. In Telegram, message @BotFather → `/newbot` → name it (e.g. "Red Mancunian
   Desk") → copy the **bot token**.
2. Message your new bot once (any text), then:
   `curl "https://api.telegram.org/bot<TOKEN>/getUpdates"` — your **chat id**
   is `result[0].message.chat.id`.

## 2. GitHub PAT for dispatches
GitHub → Settings → Developer settings → Fine-grained tokens → Generate:
- Repository access: ONLY this repo
- Permissions: **Contents: Read and write** (required for repository_dispatch)
- 1-year expiry; calendar a renewal reminder.

## 3. Repo secrets + variable
`gh secret set <NAME>` for each: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID, REPO_DISPATCH_PAT, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
GOOGLE_REFRESH_TOKEN (from step 4).
`gh variable set YOUTUBE_PRIVACY --body unlisted`  (flip to `public` after the
shakedown week).

## 4. Google / YouTube OAuth
1. console.cloud.google.com → new project "red-mancunian" → enable
   **YouTube Data API v3**.
2. OAuth consent screen: External, add yourself as test user.
3. Credentials → Create → OAuth client ID → **Desktop app** → copy client
   id + secret.
4. Locally: set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET env vars, run
   `python automation/get_refresh_token.py`, sign in as the channel owner,
   store the printed token as the GOOGLE_REFRESH_TOKEN secret.

## 5. Cloudflare Worker
```
cd automation/worker
# edit wrangler.toml GH_REPO to the real owner/repo
npx wrangler deploy
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET   # invent a long random string
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put GH_DISPATCH_PAT           # same PAT as REPO_DISPATCH_PAT
```
Register the webhook (note the secret_token must match):
```
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://red-mancunian-approval.<account>.workers.dev" \
  -d "secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

## 6. End-to-end verification (in order)
1. `python automation/telegram_bot.py alert "wiring test"` locally with the
   env vars set → message arrives on the phone.
2. Actions → editor → Run workflow with dry_run=true → artifact contains the
   MP4s (or run log explains a no-post day).
3. Actions → editor → Run workflow (dry_run=false) → video + caption + buttons
   arrive in Telegram. Tap ❌ Reject → caption gains "REJECTED".
4. Re-run, tap ✅ → publish workflow runs → reply contains an **unlisted**
   YouTube link that plays.
5. Watcher: wait for a 30-min tick or `gh workflow run news-watcher` → log
   shows "nothing new" (state already seeded).

## 7. Shakedown week, then cutover
- Keep YOUTUBE_PRIVACY=unlisted for ~a week; flip each good upload public by
  hand in YouTube Studio. When trust is earned:
  `gh variable set YOUTUBE_PRIVACY --body public`.
- Disable the local scheduled tasks ONLY after one clean breaking-news cycle:
  `schtasks /Change /TN "RedMancunian-Daily-Update" /DISABLE`
  `schtasks /Change /TN "RedMancunian-Evening-Update" /DISABLE`
- tiktok/run-daily.ps1 stays in the repo as the manual/local fallback.
```

- [ ] **Step 2: Update the PLAYBOOK automation section**

In `tiktok/PLAYBOOK.md`, replace the section starting `## Automation (scheduled runs)` (currently lines 62–82, ending just before `## Maintenance`) with:

```markdown
## Automation (cloud pipeline)
The cloud pipeline (see `automation/SETUP.md` and
`docs/superpowers/specs/2026-06-11-breaking-news-automation-design.md`) replaces
the local scheduled tasks:
- **Watcher** (GitHub Actions, every 30 min, 07:00–22:00 UK) fingerprints feed
  headlines and wakes the editor for genuinely new stories — max 3 wakes/day.
- **Editor** (GitHub Actions) runs `/mufc-update` headlessly: daily 09:00 UK
  baseline + watcher-triggered breaking runs. Renders BOTH platform videos.
- **Delivery**: each video lands in Telegram with the caption and
  ✅ Post to YouTube / ❌ Reject buttons.
- **YouTube**: approving uploads the `-youtube` MP4 automatically and replies
  with the link. TikTok stays manual from the Telegram message — save the
  video, add a trending sound at ~20%, paste the caption.
- Slow days: the editor posts nothing and says why in the run log. Evergreen
  is still interactive-only.
- Breaking news you spot yourself: Actions → editor → Run workflow, or run
  `/mufc-update` locally (still works).
- Failures arrive as Telegram alerts with a link to the run log.
```

- [ ] **Step 3: Commit**

```bash
git add automation/SETUP.md tiktok/PLAYBOOK.md
git commit -m "docs(automation): setup runbook + playbook cloud-pipeline section"
git push
```

- [ ] **Step 4: Execute the runbook**

Work through `automation/SETUP.md` sections 1–6 with the user (several steps are
interactive: BotFather, Google consent, `gh secret set`, wrangler login). The
end-to-end verification in section 6 is the acceptance test for this whole plan.

---

## Execution notes

- Tasks 2–9 are pure local TDD — no secrets needed, run in any order after
  Task 1 (but the listed order keeps imports satisfied).
- Task 10 step 7 and Task 12 step 4 need the GitHub repo + secrets and are
  interactive; do them with the user present.
- Total new surface: ~7 small Python modules + 3 workflows + 1 Worker. No
  changes to the render pipeline (`tiktok/*.py`) at all.
```
