import json
from pathlib import Path

import pytest

import story

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"


def fixture_dict():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_fixture_loads():
    s = story.load(FIXTURE)
    assert s["category"] == "TRANSFER"
    assert len(s["beats"]) == 3


def test_missing_field_rejected():
    s = fixture_dict()
    del s["hook"]
    with pytest.raises(story.StoryError, match="hook"):
        story.validate(s)


def test_bad_category_rejected():
    s = fixture_dict()
    s["category"] = "GOSSIP"
    with pytest.raises(story.StoryError, match="category"):
        story.validate(s)


def test_highlight_must_be_substring():
    s = fixture_dict()
    s["hook"]["highlight"] = "NOT IN TEXT"
    with pytest.raises(story.StoryError, match="highlight"):
        story.validate(s)


def test_rumour_requires_source():
    s = fixture_dict()
    s["source"] = ""
    with pytest.raises(story.StoryError, match="source"):
        story.validate(s)


def test_official_does_not_require_source():
    s = fixture_dict()
    s["status"] = "OFFICIAL"
    s["source"] = ""
    story.validate(s)  # must not raise


def test_beats_count_bounds():
    s = fixture_dict()
    s["beats"] = s["beats"][:1]
    with pytest.raises(story.StoryError, match="beats"):
        story.validate(s)
    s2 = fixture_dict()
    s2["beats"] = s2["beats"] * 2  # 6 beats
    with pytest.raises(story.StoryError, match="beats"):
        story.validate(s2)


def test_bad_date_rejected():
    s = fixture_dict()
    s["date"] = "11/06/2026"
    with pytest.raises(story.StoryError, match="date"):
        story.validate(s)


def test_impossible_calendar_date_rejected():
    s = fixture_dict()
    s["date"] = "2026-99-99"
    with pytest.raises(story.StoryError, match="date"):
        story.validate(s)


def test_bad_hashtag_item_rejected():
    s = fixture_dict()
    s["hashtags"] = ["#mufc", ""]
    with pytest.raises(story.StoryError, match="hashtag"):
        story.validate(s)


def test_reported_requires_source():
    s = fixture_dict()
    s["status"] = "REPORTED"
    s["source"] = ""
    with pytest.raises(story.StoryError, match="source"):
        story.validate(s)


def test_midword_highlight_rejected():
    s = fixture_dict()
    s["hook"] = {"text": "REUNITED AGAIN", "highlight": "UNITED"}
    with pytest.raises(story.StoryError, match="whole words"):
        story.validate(s)
