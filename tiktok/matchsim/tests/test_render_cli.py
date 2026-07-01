import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_render_produces_tiktoksafe_mp4(tmp_path):
    out = tmp_path / "match.mp4"
    r = subprocess.run(
        [sys.executable, CLI, "render", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21",
         "--pre", "1", "--live", "2", "--post", "1", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out.exists() and out.stat().st_size > 0
    sys.path.insert(0, str(Path(CLI).resolve().parents[1]))  # tiktok/ on path
    import video
    assert video.validate_mp4(str(out)) == []
    assert out.with_name("match-caption.txt").exists()
    assert out.with_name("match-post-notes.txt").exists()


def test_render_help_lists_subcommand():
    r = subprocess.run([sys.executable, CLI, "--help"], capture_output=True, text=True)
    assert "render" in r.stdout
