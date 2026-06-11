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


def test_corrupt_state_is_deleted_for_reseed(tmp_path, monkeypatch, capsys):
    state_path = tmp_path / "seen.json"
    state_path.write_text("{truncated")
    monkeypatch.setattr(watcher, "STATE_PATH", state_path)
    monkeypatch.setattr(watcher, "watchable_feeds",
                        lambda: [{"name": "stub", "url": "http://stub"}])
    monkeypatch.setattr(watcher, "fetch_feed", lambda url: _rss(["A story"]))
    monkeypatch.setattr(watcher, "dispatch_editor",
                        lambda h: (_ for _ in ()).throw(AssertionError("no dispatch")))
    watcher.main(now=NOON)
    assert not state_path.exists()


def test_all_feeds_down_increments_failures_and_alerts_at_threshold(tmp_path, monkeypatch):
    state_path = tmp_path / "seen.json"
    state_path.write_text(json.dumps({"stories": [], "wakes": {}, "failures": 2}))
    monkeypatch.setattr(watcher, "STATE_PATH", state_path)
    monkeypatch.setattr(watcher, "watchable_feeds",
                        lambda: [{"name": "stub", "url": "http://stub"}])
    def boom(url):
        raise OSError("down")
    monkeypatch.setattr(watcher, "fetch_feed", boom)
    alerts = []
    monkeypatch.setattr(watcher, "_alert_feeds_down", alerts.append)
    watcher.main(now=NOON)
    state = json.loads(state_path.read_text())
    assert state["failures"] == 3
    assert alerts == [3]
