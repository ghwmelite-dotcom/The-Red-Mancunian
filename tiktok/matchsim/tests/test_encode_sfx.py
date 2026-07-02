import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_rendered_mp4_has_audio_stream(tmp_path):
    out = tmp_path / "m.mp4"
    r = subprocess.run(
        [sys.executable, CLI, "render", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21",
         "--pre", "1", "--live", "2", "--post", "1", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(out)],
        capture_output=True, text=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in streams)
