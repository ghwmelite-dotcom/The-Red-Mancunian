# TikTok News Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/mufc-update` pipeline that turns daily Manchester United news into ready-to-post, Daily Mail-style 9:16 TikTok videos branded as The Red Mancunian.

**Architecture:** Claude Code acts as the editor via a slash command (fetch news → select stories → write story JSON); a deterministic Python renderer (`tiktok/render.py` + sibling modules) turns each story JSON into branded frames (Pillow) and assembles a TikTok-safe MP4 (ffmpeg). No network or AI inside the renderer — it is golden-testable with fixtures.

**Tech Stack:** Python 3.14, Pillow 12.2, ffmpeg/ffprobe 8.0 (all verified installed), pytest 9.0. Brand assets already exist in `branding/` (6 mascot poses, Anton/Bebas fonts, logo avatar).

**Spec:** `docs/superpowers/specs/2026-06-10-tiktok-news-pipeline-design.md`

**Conventions for all tasks:**
- Repo root: `C:\dev\Projects\The-Red-Mancunian` — all paths below are relative to it.
- Run tests from repo root: `python -m pytest tiktok/tests -v`
- The renderer modules live flat in `tiktok/` and import each other script-style (`import story`); tests get the path via `tiktok/tests/conftest.py`.

---

### Task 0: Git init and baseline commit

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Initialise the repository**

```bash
git init
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
tiktok/output/
```

`tiktok/output/` holds generated MP4s (large, regenerable). `tiktok/stories/` is deliberately tracked — it is the editorial record.

- [ ] **Step 3: Baseline commit of the existing project**

```bash
git add -A
git commit -m "chore: baseline commit of existing project + tiktok pipeline spec"
```

---

### Task 1: Scaffold `tiktok/` and generate the whoosh SFX

**Files:**
- Create: `tiktok/assets/whoosh.wav` (generated)
- Create: `tiktok/tests/conftest.py`
- Create: `tiktok/stories/.gitkeep`, `tiktok/output/.gitkeep`

- [ ] **Step 1: Create the folder structure**

```powershell
New-Item -ItemType Directory -Force tiktok/assets, tiktok/stories, tiktok/output, tiktok/fixtures, tiktok/tests
New-Item -ItemType File tiktok/stories/.gitkeep
New-Item -ItemType File tiktok/output/.gitkeep
```

- [ ] **Step 2: Generate the cut-whoosh SFX with ffmpeg** (synthesised pink noise — CC0 by construction, no download needed)

```bash
ffmpeg -y -f lavfi -i "anoisesrc=color=pink:duration=0.5:sample_rate=44100" \
  -af "bandpass=f=900:width_type=h:w=600,afade=t=in:st=0:d=0.08,afade=t=out:st=0.18:d=0.32,volume=0.22" \
  -ac 2 tiktok/assets/whoosh.wav
```

- [ ] **Step 3: Verify the SFX**

Run: `ffprobe -v error -show_entries format=duration -of csv=p=0 tiktok/assets/whoosh.wav`
Expected: `0.500000` (±0.01). Play it if you like — a short soft whoosh at low volume.

- [ ] **Step 4: Create `tiktok/tests/conftest.py`**

```python
import sys
from pathlib import Path

# Renderer modules live flat in tiktok/ and import each other script-style.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 5: Commit**

```bash
git add tiktok
git commit -m "feat(tiktok): scaffold pipeline folders + generated whoosh SFX"
```

---

### Task 2: Story schema module (`story.py`) + first fixture

**Files:**
- Create: `tiktok/story.py`
- Create: `tiktok/fixtures/transfer-rumour.json`
- Test: `tiktok/tests/test_story.py`

- [ ] **Step 1: Create the fixture `tiktok/fixtures/transfer-rumour.json`**

```json
{
  "id": "2026-06-11-fixture-striker-fee",
  "date": "2026-06-11",
  "category": "TRANSFER",
  "status": "RUMOUR",
  "source": "Sky Sports",
  "mood": "tension",
  "hook": { "text": "UNITED AGREE £55M FEE", "highlight": "£55M FEE" },
  "beats": [
    { "text": "PERSONAL TERMS EXPECTED THIS WEEK", "highlight": "THIS WEEK" },
    { "text": "MEDICAL PLANNED FOR FRIDAY", "highlight": "FRIDAY" },
    { "text": "A NEW NUMBER 9 AT OLD TRAFFORD", "highlight": "NUMBER 9" }
  ],
  "caption": "United have reportedly agreed a £55m fee — personal terms next. Good deal or panic buy? 🔴",
  "hashtags": ["#mufc", "#manutd", "#transfernews", "#premierleague", "#football"]
}
```

- [ ] **Step 2: Write the failing tests `tiktok/tests/test_story.py`**

```python
import copy
import json
from pathlib import Path

import pytest

import story

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"


def fixture_dict():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_valid_fixture_loads():
    s = story.load(FIXTURE)
    assert s["category"] == "TRANSFER"
    assert len(s["beats"]) == 3


def test_missing_field_rejected():
    s = fixture_dict()
    del s["hook"]
    with pytest.raises(story.StoryError, match="hook"):
        story.validate(s)


def test_bad_category_rejected():
    s = fixture_dict()
    s["category"] = "GOSSIP"
    with pytest.raises(story.StoryError, match="category"):
        story.validate(s)


def test_highlight_must_be_substring():
    s = fixture_dict()
    s["hook"]["highlight"] = "NOT IN TEXT"
    with pytest.raises(story.StoryError, match="highlight"):
        story.validate(s)


def test_rumour_requires_source():
    s = fixture_dict()
    s["source"] = ""
    with pytest.raises(story.StoryError, match="source"):
        story.validate(s)


def test_official_does_not_require_source():
    s = fixture_dict()
    s["status"] = "OFFICIAL"
    s["source"] = ""
    story.validate(s)  # must not raise


def test_beats_count_bounds():
    s = fixture_dict()
    s["beats"] = s["beats"][:1]
    with pytest.raises(story.StoryError, match="beats"):
        story.validate(s)
    s2 = fixture_dict()
    s2["beats"] = s2["beats"] * 2  # 6 beats
    with pytest.raises(story.StoryError, match="beats"):
        story.validate(s2)


def test_bad_date_rejected():
    s = fixture_dict()
    s["date"] = "11/06/2026"
    with pytest.raises(story.StoryError, match="date"):
        story.validate(s)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tiktok/tests/test_story.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'story'`

- [ ] **Step 4: Implement `tiktok/story.py`**

```python
"""Story JSON loading and validation for the TikTok news pipeline."""
import json
import re
from pathlib import Path

CATEGORIES = {"TRANSFER", "MATCHDAY", "CLUB", "ACADEMY"}
STATUSES = {"OFFICIAL", "CONFIRMED", "REPORTED", "RUMOUR"}
MOODS = {"celebrate", "tension", "roar", "react", "confident", "point"}
ATTRIBUTED = {"REPORTED", "RUMOUR"}  # must carry a source

REQUIRED = ("id", "date", "category", "status", "mood",
            "hook", "beats", "caption", "hashtags")


class StoryError(ValueError):
    pass


def _check_segment(seg, where):
    if not isinstance(seg, dict) or not isinstance(seg.get("text"), str) or not seg["text"]:
        raise StoryError(f"{where}: 'text' (non-empty string) is required")
    highlight = seg.get("highlight", "")
    if highlight and highlight not in seg["text"]:
        raise StoryError(f"{where}: highlight {highlight!r} not found in text {seg['text']!r}")


def validate(s: dict) -> dict:
    for field in REQUIRED:
        if field not in s:
            raise StoryError(f"missing required field: {field!r}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["date"]):
        raise StoryError(f"date must be YYYY-MM-DD, got {s['date']!r}")
    if s["category"] not in CATEGORIES:
        raise StoryError(f"category must be one of {sorted(CATEGORIES)}, got {s['category']!r}")
    if s["status"] not in STATUSES:
        raise StoryError(f"status must be one of {sorted(STATUSES)}, got {s['status']!r}")
    if s["mood"] not in MOODS:
        raise StoryError(f"mood must be one of {sorted(MOODS)}, got {s['mood']!r}")
    if s["status"] in ATTRIBUTED and not s.get("source"):
        raise StoryError(f"status {s['status']} requires a non-empty 'source'")
    _check_segment(s["hook"], "hook")
    if not isinstance(s["beats"], list) or not 2 <= len(s["beats"]) <= 4:
        raise StoryError("beats must be a list of 2-4 entries")
    for i, beat in enumerate(s["beats"]):
        _check_segment(beat, f"beats[{i}]")
    if not isinstance(s["caption"], str) or not s["caption"]:
        raise StoryError("caption must be a non-empty string")
    if not isinstance(s["hashtags"], list) or not s["hashtags"]:
        raise StoryError("hashtags must be a non-empty list")
    return s


def load(path) -> dict:
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tiktok/tests/test_story.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add tiktok/story.py tiktok/fixtures/transfer-rumour.json tiktok/tests/test_story.py
git commit -m "feat(tiktok): story JSON schema validation + transfer fixture"
```

---

### Task 3: Frame renderer (`frames.py`)

**Files:**
- Create: `tiktok/frames.py`
- Test: `tiktok/tests/test_frames.py`

Brand constants come from `branding/build_character.py:14-18`. Mascot poses are `branding/character/hero-0[1-6]-*.jpg`; fonts `branding/fonts/Anton.ttf` and `BebasNeue.ttf`; logo `branding/logo-avatar.png`.

- [ ] **Step 1: Write the failing tests `tiktok/tests/test_frames.py`**

```python
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
    assert len(paths) == 5
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tiktok/tests/test_frames.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'frames'`

- [ ] **Step 3: Implement `tiktok/frames.py`**

```python
"""Render branded 1080x1920 frames for a story (pure Pillow, no network)."""
import random
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "branding"
FONTS = BRAND / "fonts"
CHARACTER = BRAND / "character"
LOGO = BRAND / "logo-avatar.png"

W, H = 1080, 1920
RED = (198, 36, 30)
DRED = (120, 20, 20)
WHITE = (255, 255, 255)
CREAM = (255, 226, 222)
INK = (22, 14, 14)

HANDLE = "@theredmancunian"  # confirmed/updated with the user in Task 10
FOLLOW_LINE = "FOLLOW FOR DAILY UNITED NEWS"
FOLLOW_HIGHLIGHT = "UNITED NEWS"

POSES = {
    "react": "hero-01-react.jpg",
    "tension": "hero-02-tension.jpg",
    "celebrate": "hero-03-celebrate.jpg",
    "confident": "hero-04-confident.jpg",
    "point": "hero-05-point.jpg",
    "roar": "hero-06-roar.jpg",
}
BADGES = {
    "TRANSFER": "TRANSFER NEWS",
    "MATCHDAY": "MATCHDAY",
    "CLUB": "CLUB NEWS",
    "ACADEMY": "ACADEMY WATCH",
}

BANNER_ANGLE = 2          # degrees, Daily Mail-style tilt
BANNER_MAX_LINES = 3
BANNER_SIZES = (104, 92, 80, 68)


def check_assets():
    """Fail fast with a clear message if any brand asset is missing."""
    missing = [str(p) for p in
               [FONTS / "Anton.ttf", FONTS / "BebasNeue.ttf", LOGO,
                *(CHARACTER / f for f in POSES.values())]
               if not p.exists()]
    if missing:
        raise FileNotFoundError("missing brand assets:\n  " + "\n  ".join(missing))


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def background(seed):
    """Ink-to-dark-red vertical gradient with seeded splatter texture."""
    img = Image.new("RGB", (W, H))
    for y in range(H):
        t = y / (H - 1)
        row = tuple(round(a + (b - a) * t) for a, b in zip(INK, DRED))
        img.paste(row, (0, y, W, y + 1))
    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed)
    for _ in range(140):
        x, y = rng.randrange(W), rng.randrange(H)
        r = rng.randrange(2, 26)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*DRED, rng.randrange(20, 60)))
    return img


def paste_mascot(canvas, mood):
    """Mascot fills the upper ~62%, fading into the background at the bottom."""
    pose = Image.open(CHARACTER / POSES[mood]).convert("RGB")
    target_h = int(H * 0.62)
    scale = max(W / pose.width, target_h / pose.height)
    pose = pose.resize((round(pose.width * scale), round(pose.height * scale)))
    left = (pose.width - W) // 2
    pose = pose.crop((left, 0, left + W, target_h))
    mask = Image.new("L", (W, target_h), 255)
    md = ImageDraw.Draw(mask)
    fade_start = int(target_h * 0.72)
    for y in range(fade_start, target_h):
        alpha = round(255 * (1 - (y - fade_start) / (target_h - fade_start)))
        md.line([(0, y), (W, y)], fill=alpha)
    canvas.paste(pose, (0, 0), mask)


def _mark_highlight(text, highlight):
    """Split text into [(word, is_highlight)] using the highlight substring."""
    if not highlight:
        return [(w, False) for w in text.split()]
    pre, _, post = text.partition(highlight)
    return ([(w, False) for w in pre.split()]
            + [(w, True) for w in highlight.split()]
            + [(w, False) for w in post.split()])


def _wrap(words, fnt, max_width, probe):
    lines, line = [], []
    for item in words:
        trial = " ".join(w for w, _ in line + [item])
        if line and probe.textlength(trial, font=fnt) > max_width:
            lines.append(line)
            line = [item]
        else:
            line.append(item)
    if line:
        lines.append(line)
    return lines


def banner(text, highlight):
    """Angled black banner with white Anton caps; highlight words in red."""
    pad_x, pad_y, gap = 48, 36, 16
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    words = _mark_highlight(text, highlight)
    chosen = None
    for size in BANNER_SIZES:
        fnt = font("Anton.ttf", size)
        lines = _wrap(words, fnt, W - 160 - pad_x * 2, probe)
        if len(lines) <= BANNER_MAX_LINES:
            chosen = (fnt, lines, size)
            break
    if chosen is None:
        raise ValueError(f"headline too long even at minimum size: {text!r}")
    fnt, lines, size = chosen
    line_h = size + gap
    bw = int(max(probe.textlength(" ".join(w for w, _ in ln), font=fnt) for ln in lines)) + pad_x * 2
    bh = pad_y * 2 + line_h * len(lines) - gap
    img = Image.new("RGBA", (bw, bh), (*INK, 255))
    d = ImageDraw.Draw(img)
    y = pad_y
    for ln in lines:
        x = pad_x
        for word, hl in ln:
            d.text((x, y), word, font=fnt, fill=RED if hl else WHITE)
            x += probe.textlength(word + " ", font=fnt)
        y += line_h
    return img.rotate(BANNER_ANGLE, expand=True, resample=Image.BICUBIC)


def build_frame(s, segment, kind, index):
    seed = zlib.crc32(s["id"].encode()) + index
    cv = background(seed)
    mood = "point" if kind == "end" else s["mood"]
    paste_mascot(cv, mood)
    d = ImageDraw.Draw(cv)

    # category badge, top-left
    label = BADGES[s["category"]]
    bf = font("BebasNeue.ttf", 52)
    tw = int(d.textlength(label, font=bf))
    d.rectangle([48, 64, 48 + tw + 56, 140], fill=RED)
    d.text((76, 76), label, font=bf, fill=WHITE)

    # headline banner, lower third
    if kind == "end":
        bn = banner(FOLLOW_LINE, FOLLOW_HIGHLIGHT)
    else:
        bn = banner(segment["text"], segment.get("highlight", ""))
    by = H - bn.height - 300
    cv.paste(bn, ((W - bn.width) // 2, by), bn)

    # logo badge above the banner (Daily Mail badge position)
    logo = Image.open(LOGO).convert("RGBA").resize((148, 148))
    cv.paste(logo, ((W - 148) // 2, by - 172), logo)

    # attribution tag / handle, below the banner
    tf = font("BebasNeue.ttf", 48)
    if kind == "end":
        tag = HANDLE
    elif s["status"] in ("REPORTED", "RUMOUR"):
        tag = f'{s["status"]} - PER {s["source"].upper()}'
    else:
        tag = ""
    if tag:
        ttw = d.textlength(tag, font=tf)
        d.text(((W - ttw) / 2, by + bn.height + 20), tag, font=tf, fill=CREAM)
    return cv


def render_frames(s, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = ([("hook", s["hook"])]
           + [("beat", b) for b in s["beats"]]
           + [("end", None)])
    paths = []
    for i, (kind, seg) in enumerate(seq):
        p = out_dir / f"frame-{i:02d}-{kind}.png"
        build_frame(s, seg, kind, i).save(p)
        paths.append(p)
    return paths
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tiktok/tests/test_frames.py -v`
Expected: 4 passed

- [ ] **Step 5: Visual review of rendered frames** (acceptance check, not automated)

```powershell
python -c "import sys; sys.path.insert(0, 'tiktok'); import story, frames; frames.render_frames(story.load('tiktok/fixtures/transfer-rumour.json'), 'tiktok/output/_preview')"
Invoke-Item tiktok/output/_preview/frame-00-hook.png
```

Open each PNG and check: mascot visible and fading cleanly, banner readable with `£55M FEE` in red, `RUMOUR - PER SKY SPORTS` legible, badge top-left, logo above banner. The executor should view the frames with the Read tool and fix layout issues (overlap, clipping) before proceeding — coordinates above are a starting point, the visual is the spec.

- [ ] **Step 6: Commit**

```bash
git add tiktok/frames.py tiktok/tests/test_frames.py
git commit -m "feat(tiktok): branded frame renderer with banner, badges, mascot moods"
```

---

### Task 4: Video assembly (`video.py`)

**Files:**
- Create: `tiktok/video.py`
- Test: `tiktok/tests/test_video.py`

- [ ] **Step 1: Write the failing test `tiktok/tests/test_video.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/tests/test_video.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'video'`

- [ ] **Step 3: Implement `tiktok/video.py`**

```python
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
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
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
        cut_ms, t = [], 0.0
        for dur in durations[:-1]:
            t += dur
            cut_ms.append(round(t * 1000))
        inputs = ["-i", silent]
        delays, labels = [], []
        for j, ms in enumerate(cut_ms):
            inputs += ["-i", WHOOSH]
            delays.append(f"[{j + 1}:a]adelay={ms}|{ms}[a{j}]")
            labels.append(f"[a{j}]")
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
```

- [ ] **Step 4: Run tests to verify they pass** (this one renders + encodes, allow ~1–2 min)

Run: `python -m pytest tiktok/tests/test_video.py -v`
Expected: 2 passed

- [ ] **Step 5: Watch the test output once manually**

```powershell
python -c "import sys; sys.path.insert(0, 'tiktok'); import story, frames, video; fp = frames.render_frames(story.load('tiktok/fixtures/transfer-rumour.json'), 'tiktok/output/_preview'); video.assemble(fp, 'tiktok/output/_preview/preview.mp4')"
Invoke-Item tiktok/output/_preview/preview.mp4
```

Check: ~16s runtime, smooth slow zoom alternating direction, soft whoosh on each cut, text crisp.

- [ ] **Step 6: Commit**

```bash
git add tiktok/video.py tiktok/tests/test_video.py
git commit -m "feat(tiktok): ffmpeg assembly with ken-burns motion and cut SFX"
```

---

### Task 5: CLI entry point (`render.py`)

**Files:**
- Create: `tiktok/render.py`
- Test: `tiktok/tests/test_render.py`

- [ ] **Step 1: Write the failing test `tiktok/tests/test_render.py`**

```python
import json
from pathlib import Path

import render

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "transfer-rumour.json"


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


def test_frames_only(tmp_path):
    out = render.render_story(FIXTURE, out_root=tmp_path, frames_only=True)
    assert out is None
    frames_dir = tmp_path / "2026-06-11" / "frames" / "2026-06-11-fixture-striker-fee"
    assert len(list(frames_dir.glob("*.png"))) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/tests/test_render.py -v`
Expected: collection error — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: Implement `tiktok/render.py`**

```python
"""CLI: turn a story JSON into a ready-to-post TikTok MP4 + caption file.

Usage:
    python tiktok/render.py tiktok/stories/<story>.json [--out DIR] [--frames-only]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import frames
import story

DISCLAIMER = "Unofficial fan content - not affiliated with Manchester United FC."


def render_story(story_path, out_root=None, frames_only=False):
    s = story.load(story_path)
    frames.check_assets()
    out_root = Path(out_root) if out_root else Path(__file__).resolve().parent / "output"
    day_dir = out_root / s["date"]
    frames_dir = day_dir / "frames" / s["id"]
    frame_paths = frames.render_frames(s, frames_dir)
    if frames_only:
        print(f"frames written to {frames_dir}")
        return None

    import video  # deferred so --frames-only works without ffmpeg
    mp4 = video.assemble(frame_paths, day_dir / f"{s['id']}.mp4")
    problems = video.validate_mp4(mp4)
    if problems:
        raise RuntimeError("output failed TikTok validation: " + "; ".join(problems))

    caption = (s["caption"] + "\n\n" + " ".join(s["hashtags"])
               + "\n\n" + DISCLAIMER + "\n")
    (day_dir / f"{s['id']}-caption.txt").write_text(caption, encoding="utf-8")
    (day_dir / f"{s['id']}.json").write_text(
        json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"ready to post: {mp4}")
    return mp4


def main():
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH. Install it: winget install Gyan.FFmpeg "
                 "(then restart the terminal), or use --frames-only.")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("story", help="path to a story JSON file")
    ap.add_argument("--out", default=None, help="output root (default: tiktok/output)")
    ap.add_argument("--frames-only", action="store_true", help="render PNG frames, skip video")
    args = ap.parse_args()
    try:
        render_story(args.story, out_root=args.out, frames_only=args.frames_only)
    except (story.StoryError, FileNotFoundError, ValueError, RuntimeError) as e:
        sys.exit(f"render failed: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tiktok/tests/test_render.py -v`
Expected: 2 passed

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest tiktok/tests -v`
Expected: all tests pass (16 total)

- [ ] **Step 6: Commit**

```bash
git add tiktok/render.py tiktok/tests/test_render.py
git commit -m "feat(tiktok): render.py CLI - story JSON to posted-ready MP4 + caption"
```

---

### Task 6: Fixtures for the remaining categories + golden run

**Files:**
- Create: `tiktok/fixtures/matchday-win.json`
- Create: `tiktok/fixtures/club-official.json`
- Create: `tiktok/fixtures/academy-confirmed.json`
- Modify: `tiktok/tests/test_render.py` (add parametrized golden test)

- [ ] **Step 1: Create `tiktok/fixtures/matchday-win.json`**

```json
{
  "id": "2026-06-11-fixture-derby-win",
  "date": "2026-06-11",
  "category": "MATCHDAY",
  "status": "CONFIRMED",
  "source": "Full-time result",
  "mood": "roar",
  "hook": { "text": "UNITED WIN THE DERBY 3-1", "highlight": "WIN THE DERBY" },
  "beats": [
    { "text": "TWO GOALS IN FIVE FIRST-HALF MINUTES", "highlight": "FIVE" },
    { "text": "ACADEMY KID GETS THE THIRD", "highlight": "ACADEMY KID" },
    { "text": "OLD TRAFFORD IS BOUNCING", "highlight": "BOUNCING" }
  ],
  "caption": "3-1 in the derby and an academy kid seals it. Who was your man of the match? 🔴",
  "hashtags": ["#mufc", "#manutd", "#manchesterderby", "#premierleague", "#football"]
}
```

- [ ] **Step 2: Create `tiktok/fixtures/club-official.json`**

```json
{
  "id": "2026-06-11-fixture-contract-news",
  "date": "2026-06-11",
  "category": "CLUB",
  "status": "OFFICIAL",
  "source": "Club statement",
  "mood": "confident",
  "hook": { "text": "CAPTAIN SIGNS NEW DEAL TO 2031", "highlight": "NEW DEAL" },
  "beats": [
    { "text": "FIVE MORE YEARS AT OLD TRAFFORD", "highlight": "FIVE MORE YEARS" },
    { "text": "CLUB CONFIRMS NO RELEASE CLAUSE", "highlight": "NO RELEASE CLAUSE" }
  ],
  "caption": "It's official - the skipper stays until 2031. Right call? 🔴",
  "hashtags": ["#mufc", "#manutd", "#premierleague", "#football"]
}
```

- [ ] **Step 3: Create `tiktok/fixtures/academy-confirmed.json`**

```json
{
  "id": "2026-06-11-fixture-academy-debut",
  "date": "2026-06-11",
  "category": "ACADEMY",
  "status": "REPORTED",
  "source": "Manchester Evening News",
  "mood": "celebrate",
  "hook": { "text": "16-YEAR-OLD SET FOR FIRST-TEAM DEBUT", "highlight": "16-YEAR-OLD" },
  "beats": [
    { "text": "TOP SCORER FOR THE U18S THIS SEASON", "highlight": "TOP SCORER" },
    { "text": "TRAINED WITH THE SENIORS ALL WEEK", "highlight": "ALL WEEK" },
    { "text": "THE ACADEMY CONVEYOR BELT ROLLS ON", "highlight": "CONVEYOR BELT" }
  ],
  "caption": "Another one off the academy line - 16 and ready for the first team. Remember the name. 🔴",
  "hashtags": ["#mufc", "#manutd", "#mufcacademy", "#wonderkid", "#football"]
}
```

- [ ] **Step 4: Add a parametrized golden test to `tiktok/tests/test_render.py`**

Append:

```python
import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.parametrize("name", [
    "matchday-win", "club-official", "academy-confirmed",
])
def test_all_category_fixtures_render(name, tmp_path):
    out = render.render_story(FIXTURES / f"{name}.json", out_root=tmp_path)
    assert out is not None and out.exists()
```

- [ ] **Step 5: Run the suite**

Run: `python -m pytest tiktok/tests -v`
Expected: all pass (19 total). Note each golden render encodes a video; full suite ~3–5 min is normal.

- [ ] **Step 6: Visual spot-check one frame per category** — render `--frames-only` for each new fixture and view the hook frames (executor uses the Read tool). Confirm: OFFICIAL/CONFIRMED frames show **no** attribution tag; REPORTED/RUMOUR frames show it; each category badge reads correctly; each mood maps to a different mascot pose.

```powershell
python tiktok/render.py tiktok/fixtures/matchday-win.json --out tiktok/output/_preview --frames-only
python tiktok/render.py tiktok/fixtures/club-official.json --out tiktok/output/_preview --frames-only
python tiktok/render.py tiktok/fixtures/academy-confirmed.json --out tiktok/output/_preview --frames-only
```

- [ ] **Step 7: Commit**

```bash
git add tiktok/fixtures tiktok/tests/test_render.py
git commit -m "test(tiktok): golden fixtures for all four content categories"
```

---

### Task 7: `sources.json` with verified feeds

**Files:**
- Create: `tiktok/sources.json`

- [ ] **Step 1: Write the candidate `tiktok/sources.json`**

```json
{
  "feeds": [
    { "name": "BBC Sport - Man Utd", "tier": 1, "type": "rss", "enabled": true,
      "url": "https://feeds.bbci.co.uk/sport/football/teams/manchester-united/rss.xml" },
    { "name": "Sky Sports Football", "tier": 1, "type": "rss", "enabled": true,
      "url": "https://www.skysports.com/rss/12040" },
    { "name": "The Guardian - Man Utd", "tier": 1, "type": "rss", "enabled": true,
      "url": "https://www.theguardian.com/football/manchester-united/rss" },
    { "name": "Manchester Evening News - Man Utd", "tier": 2, "type": "rss", "enabled": true,
      "url": "https://www.manchestereveningnews.co.uk/all-about/manchester-united-fc?service=rss" },
    { "name": "Google News - Manchester United", "tier": 2, "type": "rss", "enabled": true,
      "url": "https://news.google.com/rss/search?q=%22Manchester%20United%22&hl=en-GB&gl=GB&ceid=GB:en" },
    { "name": "Man Utd official news", "tier": 1, "type": "page", "enabled": true,
      "url": "https://www.manutd.com/en/news" }
  ],
  "searches": [
    { "name": "Fabrizio Romano - United", "tier": 1, "enabled": true,
      "query": "Fabrizio Romano Manchester United transfer" },
    { "name": "David Ornstein - United", "tier": 1, "enabled": true,
      "query": "David Ornstein Manchester United" }
  ],
  "tier_meaning": {
    "1": "Can yield OFFICIAL/CONFIRMED/REPORTED status",
    "2": "REPORTED at best, always attributed",
    "3": "RUMOUR only, always attributed (tabloids surface via Google News)"
  }
}
```

- [ ] **Step 2: Verify every enabled RSS/page URL live** — the executor must WebFetch each `url` and confirm it returns current Man Utd content. For any feed that 404s or has moved: find the current URL (WebSearch), fix the entry, or set `"enabled": false` with the reason appended to the name. Do not leave a broken feed enabled.

- [ ] **Step 3: Commit**

```bash
git add tiktok/sources.json
git commit -m "feat(tiktok): news source registry with reliability tiers (verified live)"
```

---

### Task 8: `PLAYBOOK.md`

**Files:**
- Create: `tiktok/PLAYBOOK.md`

- [ ] **Step 1: Write `tiktok/PLAYBOOK.md`**

```markdown
# The Red Mancunian — TikTok News Playbook

The format: Daily Mail Sport-style news cards, Red Mancunian skin.
One story per video. Hook → 2–4 beats → follow card. 15–25 seconds.

## Copy rules
- **Hook:** ≤ 8 words, present tense, ONE highlighted phrase. No clickbait lies —
  the video must deliver what the hook promises.
- **Beats:** ≤ 12 words each. Every beat advances the story. Cut padding.
- **Highlights:** the highlight substring must appear verbatim in the text.
  Highlight the number, the name, or the stake — the thing eyes should catch.
- **Rumours:** never presented as fact. status RUMOUR/REPORTED requires a source,
  which renders in-frame ("RUMOUR - PER SKY SPORTS") and should be echoed in caption.
- **Caption:** 1–2 sentences + an engagement question + hashtags. The renderer
  appends the disclaimer line automatically.

## Status ladder
| Status | Use when | Frame tag |
|---|---|---|
| OFFICIAL | Club statement / announcement | none |
| CONFIRMED | Multiple tier-1 outlets report as done | none |
| REPORTED | One tier-1/2 outlet reports | shown |
| RUMOUR | Tabloid / aggregator / speculation | shown |

## Hashtag base set
`#mufc #manutd #premierleague #football` + per category:
- TRANSFER: `#transfernews #transferwindow`
- MATCHDAY: `#matchday` + opponent tag (e.g. `#manchesterderby`)
- CLUB: story-specific
- ACADEMY: `#mufcacademy #wonderkid`

## Cadence
- Baseline: 1 post/day.
- Surge (2–3/day): matchdays, transfer deadline period, genuine breaking news.
- Slow day: ACADEMY/nostalgia evergreen, or post nothing. Never force a non-story.

## Posting workflow (per video)
1. Watch the MP4 in `tiktok/output/<date>/` start to finish.
2. Open TikTok → upload the MP4.
3. Add a trending sound, volume LOW (~20%) under the video. This is why we don't
   bake music in — trending sounds boost reach.
4. Paste the caption from `<id>-caption.txt`.
5. Post times (UK): 12:00–14:00 or 19:00–21:00. Breaking news: post immediately.
6. First hour: reply to early comments — it feeds the algorithm.

## Maintenance
- Feeds live in `sources.json` — disable dead ones, add new ones with a tier.
- Template changes: edit `frames.py`, run `python -m pytest tiktok/tests`,
  visually review `tiktok/output/_preview` frames before the next live run.
```

- [ ] **Step 2: Commit**

```bash
git add tiktok/PLAYBOOK.md
git commit -m "docs(tiktok): playbook - copy rules, status ladder, posting workflow"
```

---

### Task 9: The `/mufc-update` slash command

**Files:**
- Create: `.claude/commands/mufc-update.md`

- [ ] **Step 1: Write `.claude/commands/mufc-update.md`**

```markdown
---
description: Produce today's Red Mancunian TikTok video(s) from live Man Utd news
---

You are the editor of The Red Mancunian TikTok account. Produce today's ready-to-post
video(s). Follow `tiktok/PLAYBOOK.md` for copy rules and `tiktok/sources.json` for feeds.

## 1. Fetch
- WebFetch every enabled feed in `tiktok/sources.json` (prompt: "list today's
  Manchester United stories: headline, 1-line summary, date"). Skip dead feeds with a
  note — never abort the run over one feed.
- Run the enabled `searches` via WebSearch for reporter-only stories (Romano, Ornstein).
- Only use stories from the last 24 hours (48h on slow days).

## 2. Edit
- Dedupe across sources. For each distinct story note: best source + tier, category
  (TRANSFER / MATCHDAY / CLUB / ACADEMY), status per the PLAYBOOK status ladder.
- Newsworthiness score (1-10). 8+: post immediately regardless of cadence. Guide:
  confirmed signing 9-10, medical/fee agreed 8, big rumour 6-7, manager presser
  quote 5-6, injury news 5-7 by player importance, derby result 9, routine result 7.

## 3. Select
- Normal day: the 1 best story (score ≥ 5). Big day (matchday, deadline window,
  breaking): up to 3, each ≥ 6.
- Nothing ≥ 5? Offer an ACADEMY/nostalgia evergreen instead, or recommend not
  posting today. Never force a non-story. Ask the user before rendering evergreen.

## 4. Write
For each selected story, write `tiktok/stories/YYYY-MM-DD-<slug>.json` matching the
schema in `tiktok/story.py` (see fixtures in `tiktok/fixtures/` for examples).
- Mood mapping: confirmed signing/academy joy → celebrate; rumour/ongoing saga →
  tension; win/derby → roar; breaking/shock → react; club business → confident.
- Date field = today (YYYY-MM-DD). Hook ≤ 8 words. Beats 2-4, ≤ 12 words each.
  Highlights must be verbatim substrings.

## 5. Render
For each story JSON:
    python tiktok/render.py tiktok/stories/<file>.json
If render fails on copy issues (highlight mismatch, too-long headline), fix the JSON
and re-run. Output lands in `tiktok/output/<date>/`.

## 6. Report
End with a summary the user can act on:
- For each video: file path, hook, category/status/source, score, and why it was chosen
- What was considered and skipped (one line each)
- Posting note: suggested post time per PLAYBOOK + "add a trending sound at ~20%
  volume in the TikTok app"
- Any feed problems found (so sources.json can be updated)
```

- [ ] **Step 2: Verify the command is picked up**

Run `/mufc-update` appears in the slash-command list (restart Claude Code session if needed). Do not execute it yet — that's Task 10.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/mufc-update.md
git commit -m "feat(tiktok): /mufc-update editorial slash command"
```

---

### Task 10: Live end-to-end run + README

**Files:**
- Modify: `README.md` (folder contents section)

- [ ] **Step 1: Run `/mufc-update` for real** — full live test: fetch today's actual news, write real story JSON, render real MP4(s). The user reviews the video(s) before anything is posted.

- [ ] **Step 2: Fix whatever the live run surfaces** (dead feeds → update `sources.json`; copy/layout issues → fix and re-run; renderer bugs → fix with a test reproducing the issue first).

- [ ] **Step 3: Update `README.md`** — add to the folder-contents tree:

```
├── tiktok/                        ← daily TikTok news pipeline (see tiktok/PLAYBOOK.md)
│   ├── PLAYBOOK.md                ← format rules + posting workflow
│   ├── sources.json               ← news feeds + reliability tiers
│   ├── render.py                  ← story JSON → ready-to-post MP4 (run /mufc-update)
│   └── output/YYYY-MM-DD/         ← finished videos + captions
```

And under the quick-start checklist add: `- [ ] Daily: run /mufc-update in Claude Code, review, post (see tiktok/PLAYBOOK.md)`

- [ ] **Step 4: Confirm the TikTok handle** — ask the user for the real handle and update `HANDLE` in `tiktok/frames.py` if it differs from `@theredmancunian`. Re-run `python -m pytest tiktok/tests/test_frames.py -v` after changing it.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(tiktok): live pipeline verified end-to-end + README"
```
