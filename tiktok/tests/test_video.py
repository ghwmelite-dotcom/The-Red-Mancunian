from pathlib import Path

import pytest

import frames
import story
import video

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"


def test_assemble_produces_valid_tiktok_mp4(tmp_path):
    s = story.load(FIXTURE)
    frame_paths = frames.render_frames(s, tmp_path / "frames")
    mp4 = video.assemble(frame_paths, tmp_path / "out.mp4")
    assert mp4.exists()
    assert video.validate_mp4(mp4) == []


def test_validate_flags_bad_file(tmp_path):
    bad = tmp_path / "not-a-video.mp4"
    bad.write_bytes(b"junk")
    with pytest.raises(Exception):
        video.validate_mp4(bad)


def test_cut_times_between_segments_only():
    assert video._cut_times_ms([3.0, 3.5, 3.5, 3.5, 2.0]) == [3000, 6500, 10000, 13500]
    assert video._cut_times_ms([3.0]) == []
    assert video._cut_times_ms([]) == []


def test_assemble_single_frame_produces_valid_mp4(tmp_path):
    s = story.load(FIXTURE)
    frame_paths = frames.render_frames(s, tmp_path / "frames")
    mp4 = video.assemble(frame_paths[:1], tmp_path / "single.mp4")
    assert video.validate_mp4(mp4) == []
