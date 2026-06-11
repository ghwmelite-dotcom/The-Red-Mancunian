"""Assemble rendered frames into a TikTok-safe MP4 (h264/yuv420p/AAC, 1080x1920)."""
import json
import subprocess
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
WHOOSH = ASSETS / "whoosh.wav"
FPS = 30
DURATIONS = {"hook": 3.0, "beat": 3.5, "end": 2.0}


def _run(cmd):
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                         errors="replace")
    if res.returncode != 0:
        raise RuntimeError(f"command failed: {cmd[0]}\n{res.stderr[-2000:]}")
    return res


def _segment(frame_png, duration, zoom_in, out_path):
    """One ken-burns segment from a still: slow zoom, alternating direction."""
    n = round(duration * FPS)
    z = (f"min(1.0+0.0009*on,1.10)" if zoom_in else f"max(1.10-0.0009*on,1.0)")
    vf = (f"scale=2160:3840,"
          f"zoompan=z='{z}':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":s=1080x1920:fps={FPS},format=yuv420p")
    _run(["ffmpeg", "-y", "-loop", "1", "-i", frame_png, "-vf", vf,
          "-t", f"{duration}", "-c:v", "libx264", "-preset", "medium", "-an", out_path])


def _cut_times_ms(durations):
    """Cut points between segments in ms (no cut at t=0 or after the last segment)."""
    cuts, t = [], 0.0
    for dur in durations[:-1]:
        t += dur
        cuts.append(round(t * 1000))
    return cuts


def assemble(frame_paths, out_mp4):
    frame_paths = [Path(p) for p in frame_paths]
    durations = [DURATIONS[p.stem.split("-")[-1]] for p in frame_paths]
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        segs = []
        for i, (p, dur) in enumerate(zip(frame_paths, durations)):
            seg = td / f"seg{i}.mp4"
            _segment(p, dur, zoom_in=(i % 2 == 0), out_path=seg)
            segs.append(seg)

        concat = td / "concat.txt"
        concat.write_text("".join(f"file '{s.as_posix()}'\n" for s in segs), encoding="utf-8")
        silent = td / "video.mp4"
        _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat,
              "-c", "copy", silent])

        # a quiet whoosh at every cut so the file is not silent
        total = sum(durations)
        cut_ms = _cut_times_ms(durations)

        if not cut_ms:
            # single segment: no cuts, so skip the SFX mix entirely and add a
            # silent AAC track so the output is still a valid MP4.
            _run(["ffmpeg", "-y", "-i", silent,
                  "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                  "-map", "0:v", "-map", "1:a",
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                  "-t", f"{total}", "-movflags", "+faststart", out_mp4])
            return out_mp4

        inputs = ["-i", silent]
        delays, labels = [], []
        for j, ms in enumerate(cut_ms):
            inputs += ["-i", WHOOSH]
            delays.append(f"[{j + 1}:a]adelay={ms}|{ms}[a{j}]")
            labels.append(f"[a{j}]")
        # -t total is the source of truth for output length; apad extends the
        # short whoosh mix to fill it.
        fc = (";".join(delays) + ";" + "".join(labels)
              + f"amix=inputs={len(labels)}:normalize=0,apad[aout]")
        _run(["ffmpeg", "-y", *inputs, "-filter_complex", fc,
              "-map", "0:v", "-map", "[aout]",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
              "-t", f"{total}", "-movflags", "+faststart", out_mp4])
    return out_mp4


def validate_mp4(path):
    """Return a list of problems; [] means TikTok-safe."""
    res = _run(["ffprobe", "-v", "error", "-print_format", "json",
                "-show_streams", "-show_format", path])
    info = json.loads(res.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    problems = []
    if v is None:
        return ["no video stream"]
    if (v["width"], v["height"]) != (1080, 1920):
        problems.append(f"resolution {v['width']}x{v['height']}, want 1080x1920")
    if v["codec_name"] != "h264":
        problems.append(f"video codec {v['codec_name']}, want h264")
    if v.get("pix_fmt") != "yuv420p":
        problems.append(f"pix_fmt {v.get('pix_fmt')}, want yuv420p")
    if a is None or a["codec_name"] != "aac":
        problems.append("audio missing or not aac")
    if float(info["format"]["duration"]) > 60:
        problems.append("duration over 60s")
    return problems
