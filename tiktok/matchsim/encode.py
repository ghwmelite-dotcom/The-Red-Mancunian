"""Encode a PNG frame sequence (f%05d.png) into a TikTok-safe MP4:
h264 / yuv420p / 1080x1920, with an AAC audio track.

`sfx_events` is a list of (time_seconds, gain) — the whoosh clip is delayed to
each time and mixed. Used for act transitions (normal gain) and goals (louder).
If no events are given, a silent track is added so the file stays valid.
"""
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
WHOOSH = ASSETS / "whoosh.wav"


def _run(cmd):
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                         errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{res.stderr[-2000:]}")
    return res


def encode(frames_dir, out_mp4, fps=30, sfx_events=None, duration=None):
    frames_dir = Path(frames_dir)
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    vin = ["-framerate", str(fps), "-i", str(frames_dir / "f%05d.png")]

    if not sfx_events or not WHOOSH.exists():
        cmd = ["ffmpeg", "-y", *vin,
               "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-map", "0:v", "-map", "1:a", "-shortest",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
               "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", str(out_mp4)]
        _run(cmd)
        return out_mp4

    inputs, delays, labels = [], [], []
    for j, (t, gain) in enumerate(sfx_events):
        ms = max(0, round(t * 1000))
        inputs += ["-i", str(WHOOSH)]
        delays.append(f"[{j + 1}:a]adelay={ms}|{ms},volume={gain}[a{j}]")
        labels.append(f"[a{j}]")
    fc = ";".join(delays) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0,apad[aout]"
    cmd = ["ffmpeg", "-y", *vin, *inputs, "-filter_complex", fc,
           "-map", "0:v", "-map", "[aout]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-crf", "19", "-preset", "medium", "-c:a", "aac", "-b:a", "128k",
           "-shortest", "-movflags", "+faststart", str(out_mp4)]
    _run(cmd)
    return out_mp4
