import json
from pathlib import Path

import pytest

import render
import story

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_full_render_outputs(tmp_path):
    out = render.render_story(FIXTURE, out_root=tmp_path)
    sid = "2026-06-11-fixture-striker-fee"
    day = tmp_path / "2026-06-11"
    assert out == day / f"{sid}.mp4"
    assert out.exists()
    caption = (day / f"{sid}-caption.txt").read_text(encoding="utf-8")
    assert "panic buy" in caption
    assert "#mufc" in caption
    assert "Unofficial fan content" in caption
    assert (day / f"{sid}.json").exists()
    notes = (day / f"{sid}-post-notes.txt").read_text(encoding="utf-8")
    assert "12:00" in notes  # TikTok lunch window
    assert "trending sound" in notes
    # post time must never leak into the paste-ready caption
    assert "12:00" not in caption


def test_frames_only(tmp_path):
    out = render.render_story(FIXTURE, out_root=tmp_path, frames_only=True)
    assert out is None
    frames_dir = tmp_path / "2026-06-11" / "frames" / "2026-06-11-fixture-striker-fee"
    assert len(list(frames_dir.glob("*.png"))) == 5  # hook + 3 beats + end


def test_invalid_story_raises_story_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"id": "x"}', encoding="utf-8")
    with pytest.raises(story.StoryError):
        render.render_story(bad, out_root=tmp_path, frames_only=True)


def test_rerender_clears_stale_frames(tmp_path):
    render.render_story(FIXTURE, out_root=tmp_path, frames_only=True)
    frames_dir = tmp_path / "2026-06-11" / "frames" / "2026-06-11-fixture-striker-fee"
    (frames_dir / "frame-99-beat.png").write_bytes(b"stale")
    render.render_story(FIXTURE, out_root=tmp_path, frames_only=True)
    assert not (frames_dir / "frame-99-beat.png").exists()
    assert len(list(frames_dir.glob("*.png"))) == 5  # hook + 3 beats + end


@pytest.mark.parametrize("name", [
    "matchday-win", "club-official", "academy-confirmed",
])
def test_all_category_fixtures_render(name, tmp_path):
    out = render.render_story(FIXTURES / f"{name}.json", out_root=tmp_path)
    assert out is not None and out.exists()


def test_youtube_platform_outputs_suffixed(tmp_path):
    out = render.render_story(FIXTURE, out_root=tmp_path, platform="youtube")
    sid = "2026-06-11-fixture-striker-fee"
    day = tmp_path / "2026-06-11"
    assert out == day / f"{sid}-youtube.mp4"
    assert out.exists()
    assert (day / f"{sid}-youtube-caption.txt").exists()
    # youtube frames live in their own dir so both platforms can coexist per day
    assert (day / "frames" / f"{sid}-youtube" / "frame-04-end.png").exists()
    notes = (day / f"{sid}-youtube-post-notes.txt").read_text(encoding="utf-8")
    assert "19:00" in notes  # YouTube evening window
    assert "UNITED AGREE £55M FEE" in notes  # suggested title built from the hook
