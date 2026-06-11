import json
from pathlib import Path

import pytest
from PIL import Image

import frames
import story

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"


@pytest.fixture(scope="module")
def fixture_story():
    return story.load(FIXTURE)


def test_check_assets_passes():
    frames.check_assets()  # must not raise on this machine


def test_renders_hook_beats_end(fixture_story, tmp_path):
    paths = frames.render_frames(fixture_story, tmp_path)
    # hook + 3 beats + end frame
    assert len(paths) == 5  # hook + 3 beats + end = 5
    assert paths[0].name == "frame-00-hook.png"
    assert paths[-1].name == "frame-04-end.png"
    for p in paths:
        img = Image.open(p)
        assert img.size == (1080, 1920)


def test_rendering_is_deterministic(fixture_story, tmp_path):
    a = frames.render_frames(fixture_story, tmp_path / "a")
    b = frames.render_frames(fixture_story, tmp_path / "b")
    assert a[0].read_bytes() == b[0].read_bytes()


def test_overlong_headline_raises(fixture_story, tmp_path):
    s = json.loads(FIXTURE.read_text(encoding="utf-8"))
    s["hook"]["text"] = "THIS HEADLINE IS FAR FAR TOO LONG TO EVER FIT ON THE BANNER " * 4
    s["hook"]["highlight"] = ""
    with pytest.raises(ValueError, match="too long"):
        frames.render_frames(s, tmp_path)


def test_mark_highlight_whole_words():
    assert frames._mark_highlight("UNITED AGREE FEE", "FEE") == [
        ("UNITED", False), ("AGREE", False), ("FEE", True)]


def test_mark_highlight_rejects_midword():
    with pytest.raises(ValueError, match="whole words"):
        frames._mark_highlight("MONDAY DERBY", "DAY")
    with pytest.raises(ValueError, match="whole words"):
        frames._mark_highlight("REUNITED AGAIN", "UNITED")


def test_mark_highlight_marks_all_occurrences():
    assert frames._mark_highlight("CITY BEAT CITY", "CITY") == [
        ("CITY", True), ("BEAT", False), ("CITY", True)]


def test_mark_highlight_empty():
    assert frames._mark_highlight("ONE TWO", "") == [("ONE", False), ("TWO", False)]


def test_pose_and_badge_maps_cover_schema():
    assert frames.BADGES.keys() == story.CATEGORIES
    assert frames.POSES.keys() == story.MOODS


def test_platform_changes_only_end_frame(fixture_story, tmp_path):
    tiktok = frames.render_frames(fixture_story, tmp_path / "tt", platform="tiktok")
    youtube = frames.render_frames(fixture_story, tmp_path / "yt", platform="youtube")
    # hook/beat frames identical across platforms; end card differs (handle + verb)
    assert tiktok[0].read_bytes() == youtube[0].read_bytes()
    assert tiktok[-1].read_bytes() != youtube[-1].read_bytes()


def test_unknown_platform_rejected(fixture_story, tmp_path):
    with pytest.raises(KeyError):
        frames.render_frames(fixture_story, tmp_path, platform="instagram")
