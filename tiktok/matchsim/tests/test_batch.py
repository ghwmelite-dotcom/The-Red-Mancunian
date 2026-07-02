import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_batch_renders_all_fixtures(tmp_path):
    fixtures = [
        {"home": "MUN", "away": "RMA", "competition": "ucl", "seed": 1},
        {"home": "LIV", "away": "ARS", "competition": "epl", "seed": 2},
    ]
    fx_file = tmp_path / "fixtures.json"
    fx_file.write_text(json.dumps(fixtures), encoding="utf-8")
    out_dir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, CLI, "batch", "--fixtures", str(fx_file),
         "--out-dir", str(out_dir), "--pre", "1", "--live", "1", "--post", "1"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (out_dir / "mun-vs-rma.mp4").exists()
    assert (out_dir / "liv-vs-ars.mp4").exists()


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_batch_isolates_a_failing_fixture(tmp_path):
    fixtures = [
        {"home": "MUN", "away": "RMA", "competition": "ucl", "seed": 1},
        {"home": "ZZZ", "away": "RMA", "competition": "ucl", "seed": 2},
    ]
    fx_file = tmp_path / "fixtures.json"
    fx_file.write_text(json.dumps(fixtures), encoding="utf-8")
    out_dir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, CLI, "batch", "--fixtures", str(fx_file),
         "--out-dir", str(out_dir), "--pre", "1", "--live", "1", "--post", "1"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert (out_dir / "mun-vs-rma.mp4").exists()
    assert not (out_dir / "zzz-vs-rma.mp4").exists()


def test_render_caption_includes_competition_hashtag(tmp_path):
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    out = tmp_path / "m.mp4"
    subprocess.run(
        [sys.executable, CLI, "render", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21",
         "--pre", "1", "--live", "1", "--post", "1", "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    caption = out.with_name("m-caption.txt").read_text(encoding="utf-8")
    assert "#ucl" in caption
