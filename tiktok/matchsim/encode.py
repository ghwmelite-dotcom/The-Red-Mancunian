"""Encode a PNG frame sequence (f%05d.png) into a TikTok-safe MP4:
h264 / yuv420p / 1080x1920, with a silent AAC track so the file is valid.
SFX is Plan 4.
"""
import subprocess
from pathlib import Path


def encode(frames_dir, out_mp4, fps=30):
    frames_dir = Path(frames_dir)
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "f%05d.png"),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-map", "0:v", "-map", "1:a", "-shortest",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-crf", "19", "-preset", "medium",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", str(out_mp4),
    ]
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                         errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{res.stderr[-2000:]}")
    return out_mp4
