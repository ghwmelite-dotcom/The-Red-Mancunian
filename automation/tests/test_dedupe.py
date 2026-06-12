import json
from datetime import datetime
from zoneinfo import ZoneInfo

import dedupe

LONDON = ZoneInfo("Europe/London")
NOW = datetime(2026, 6, 12, 18, 0, tzinfo=LONDON)

FERNANDES = {
    "hook": {"text": "UNITED IN FORMAL TALKS FOR FERNANDES"},
    "beats": [{"text": "WEST HAM VALUE THE MIDFIELDER AT £80M"},
              {"text": "ROMANO CONFIRMS UNITED ARE IN THE RACE"},
              {"text": "PSG LURK BUT FERNANDES PREFERS UNITED"}],
}
FERNANDES_REWRITE = {
    "hook": {"text": "FORMAL TALKS OPENED FOR FERNANDES"},
    "beats": [{"text": "WEST HAM WANT £80M FOR THE MIDFIELDER"},
              {"text": "ROMANO CONFIRMS THE RACE IS ON"},
              {"text": "FERNANDES PREFERS UNITED OVER PSG"}],
}
FERNANDES_FOLLOWUP = {
    "hook": {"text": "FERNANDES FEE AGREED — MEDICAL BOOKED"},
    "beats": [{"text": "£80M DEAL DONE WITH WEST HAM"},
              {"text": "MEDICAL SCHEDULED FOR MONDAY"},
              {"text": "CONTRACT UNTIL 2031 — HERE WE GO"}],
}
OTHER_STORY = {
    "hook": {"text": "HALL LEFT OUT OF ENGLAND SQUAD"},
    "beats": [{"text": "TUCHEL NAMES 26 FOR THE WORLD CUP"},
              {"text": "NO PLACE FOR THE UNITED LEFT-BACK"}],
}


def _entry(story_id, story, sent_at):
    return {"id": story_id, "tokens": sorted(dedupe.story_tokens(story)),
            "sent_at": sent_at.isoformat()}


def test_same_id_is_duplicate():
    ledger = [_entry("2026-06-12-fernandes-talks", FERNANDES, NOW)]
    sig = dedupe.story_tokens(FERNANDES)
    assert dedupe.duplicate_of("2026-06-12-fernandes-talks", sig, ledger)


def test_rewrite_of_same_story_is_duplicate():
    ledger = [_entry("2026-06-12-fernandes-talks", FERNANDES, NOW)]
    sig = dedupe.story_tokens(FERNANDES_REWRITE)
    assert dedupe.duplicate_of("2026-06-12-fernandes-race", sig, ledger) == \
        "2026-06-12-fernandes-talks"


def test_status_followup_is_not_duplicate():
    ledger = [_entry("2026-06-12-fernandes-talks", FERNANDES, NOW)]
    sig = dedupe.story_tokens(FERNANDES_FOLLOWUP)
    assert dedupe.duplicate_of("2026-06-13-fernandes-fee-agreed", sig, ledger) is None


def test_unrelated_story_is_not_duplicate():
    ledger = [_entry("2026-06-12-fernandes-talks", FERNANDES, NOW)]
    sig = dedupe.story_tokens(OTHER_STORY)
    assert dedupe.duplicate_of("2026-06-12-hall-england-snub", sig, ledger) is None


def test_load_missing_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(dedupe, "LEDGER_PATH", tmp_path / "delivered.json")
    assert dedupe.load(now=NOW) == []


def test_load_prunes_old_entries(tmp_path, monkeypatch):
    path = tmp_path / "delivered.json"
    monkeypatch.setattr(dedupe, "LEDGER_PATH", path)
    old = NOW.replace(month=5, day=1)
    path.write_text(json.dumps([_entry("old", OTHER_STORY, old),
                                _entry("fresh", FERNANDES, NOW)]), encoding="utf-8")
    assert [e["id"] for e in dedupe.load(now=NOW)] == ["fresh"]


def test_record_appends_and_persists(tmp_path, monkeypatch):
    path = tmp_path / "delivered.json"
    monkeypatch.setattr(dedupe, "LEDGER_PATH", path)
    ledger = []
    dedupe.record(ledger, "2026-06-12-fernandes-talks",
                  dedupe.story_tokens(FERNANDES), now=NOW)
    assert ledger[0]["id"] == "2026-06-12-fernandes-talks"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == ledger
