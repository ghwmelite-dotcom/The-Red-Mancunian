from pathlib import Path
from PIL import Image
from engine import simulate
from prepare import prepare
from timeline import build_timeline
from render_match import render_frames


def _tl_and_bundle():
    b = prepare(simulate("MUN", "RMA", competition="ucl", seed=21), n_frames=90)
    tl = build_timeline(b, pre=1.0, live=2.0, post=1.0)  # 30+60+30 = 120
    return b, tl


def test_writes_one_png_per_timeline_frame(tmp_path):
    b, tl = _tl_and_bundle()
    paths = render_frames(b, tl, tmp_path)
    assert len(paths) == tl["total"]
    assert all(Path(p).exists() for p in paths)


def test_frames_are_full_canvas(tmp_path):
    b, tl = _tl_and_bundle()
    paths = render_frames(b, tl, tmp_path)
    for p in (paths[0], paths[len(paths) // 2], paths[-1]):
        with Image.open(p) as im:
            assert im.size == (1080, 1920)


def test_deterministic_first_frame_bytes(tmp_path):
    b, tl = _tl_and_bundle()
    p1 = render_frames(b, tl, tmp_path / "a")
    p2 = render_frames(b, tl, tmp_path / "b")
    assert Path(p1[0]).read_bytes() == Path(p2[0]).read_bytes()
