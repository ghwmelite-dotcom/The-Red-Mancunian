# MatchSim Renderer Implementation Plan (Plan 3 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a render-ready bundle (`{match, theme, motion}` from Plan 2) into a watchable, TikTok-safe **1080×1920 30fps MP4** with three acts (pre-match hype → live arena sim → full-time analytics), plus a caption file and post-notes, via a `render` CLI subcommand.

**Architecture:** Pure/testable modules first — `timeline.py` (aligns match-minutes to video frames: act boundaries, per-live-frame clock/score/interpolated win-prob, goal frames, motion index), `colors.py` (hex/rgb + lerp), `layout.py` (zone rectangles for the live frame). Then Pillow drawing — `draw.py` (brand-font text, glossy orbs, glass panels, gradient background, win-prob bar, scoreboard) reusing the `make_video.py` technique, and `render_match.py` (composes the three acts into a PNG frame sequence driven by the timeline). Finally `encode.py` (PNG sequence → h264/yuv420p MP4 + silent AAC, reusing `tiktok/video.py:validate_mp4`) wired into a `render` CLI subcommand that also writes `-caption.txt` and `-post-notes.txt` (parity with `tiktok/render.py`).

**Tech Stack:** Python 3, Pillow (installed, 12.x), ffmpeg/ffprobe (installed, v8), `pytest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-01-matchsim-design.md` (milestones M3 + M4). Prior work (engine + arena/theming, Plans 1–2) is on this branch.

**Conventions (unchanged):** `tiktok/matchsim/` is a plain module dir (NO `__init__.py`); bare imports; `tests/conftest.py` puts the dir on `sys.path`; run commands from repo root `C:\dev\Projects\The-Red-Mancunian`; determinism via seeded inputs (the renderer itself is a pure function of the bundle — no randomness).

**Deferred to Plan 4 (do NOT build here):** goal-replay slow-mo / shot tracer / confetti, SFX mux (whoosh/clash/roar), batch mode, crest-image drop-in, per-competition visual QA, momentum meter / ticker scroll animation polish.

**Key facts for implementers:**
- Brand fonts exist at `branding/fonts/Anton.ttf` and `branding/fonts/BebasNeue.ttf` (absolute base: `C:/dev/Projects/The-Red-Mancunian/branding/fonts`).
- The bundle shape (from `python tiktok/matchsim/cli.py prepare ...`): `bundle["match"]` has `fixture` (home/away discs with `name/abbr/color/monogram/crest`, plus `competition/stage/venue/date/seed/final`), `events` (goal/near_miss/half_time/full_time), `winprob` (list of `{minute,home,draw,away}`), `analytics` (`{possession:[h,a],shots:[h,a],xg:[h,a]}`). `bundle["theme"]` has `key/name/bg[3 hex]/accent/gold/text/muted/trophy/ticker/frame_glow/united_home`. `bundle["motion"]` is a list of `{home:[x,y],away:[x,y],ball:[x,y],clash:bool}` with coords in the unit circle (radius 1).
- Reuse `tiktok/video.py`'s `validate_mp4(path)` for the encode smoke test (returns `[]` when the MP4 is 1080×1920 h264/yuv420p/aac ≤60s).

---

### Task 1: Colour helpers

**Files:**
- Create: `tiktok/matchsim/colors.py`
- Test: `tiktok/matchsim/tests/test_colors.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_colors.py`:

```python
import pytest
from colors import hex_to_rgb, rgb_to_hex, lerp_rgb


def test_hex_to_rgb():
    assert hex_to_rgb("#DA020E") == (218, 2, 14)
    assert hex_to_rgb("39e6e6") == (57, 230, 230)


def test_rgb_to_hex_roundtrip():
    assert rgb_to_hex((218, 2, 14)) == "#DA020E"
    assert hex_to_rgb(rgb_to_hex((1, 2, 3))) == (1, 2, 3)


def test_lerp_endpoints_and_mid():
    a, b = (0, 0, 0), (100, 200, 50)
    assert lerp_rgb(a, b, 0.0) == (0, 0, 0)
    assert lerp_rgb(a, b, 1.0) == (100, 200, 50)
    assert lerp_rgb(a, b, 0.5) == (50, 100, 25)


def test_lerp_clamps_out_of_range():
    a, b = (0, 0, 0), (100, 100, 100)
    assert lerp_rgb(a, b, -1.0) == (0, 0, 0)
    assert lerp_rgb(a, b, 2.0) == (100, 100, 100)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_colors.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `tiktok/matchsim/colors.py`:

```python
"""Small colour helpers for the renderer: hex<->rgb and linear interpolation."""


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % (rgb[0], rgb[1], rgb[2])


def lerp_rgb(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_colors.py -v` → 4 passed.

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/colors.py tiktok/matchsim/tests/test_colors.py
git commit -m "feat(matchsim): colour helpers (hex/rgb + lerp)"
```

---

### Task 2: Frame timeline (minute↔frame alignment)

**Files:**
- Create: `tiktok/matchsim/timeline.py`
- Test: `tiktok/matchsim/tests/test_timeline.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_timeline.py`:

```python
from engine import simulate
from prepare import prepare
from timeline import build_timeline, FPS


def _bundle(seed=21, frames=120):
    m = simulate("MUN", "RMA", competition="ucl", seed=seed)
    return prepare(m, n_frames=frames)


def test_total_and_acts():
    tl = build_timeline(_bundle(), fps=30, pre=2.0, live=4.0, post=2.0)
    assert tl["fps"] == 30
    assert tl["total"] == 60 + 120 + 60
    assert len(tl["frames"]) == tl["total"]
    pre, live, post = tl["acts"]["pre"], tl["acts"]["live"], tl["acts"]["post"]
    assert pre == (0, 60)
    assert live == (60, 180)
    assert post == (180, 240)


def test_frames_carry_their_act():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    acts = [f["act"] for f in tl["frames"]]
    assert acts[0] == "pre"
    assert acts[tl["acts"]["live"][0]] == "live"
    assert acts[-1] == "post"


def test_live_minute_runs_zero_to_ninety_monotonic():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    minutes = [f["minute"] for f in live]
    assert minutes[0] == 0.0
    assert abs(minutes[-1] - 90.0) < 1e-6
    assert minutes == sorted(minutes)


def test_live_clock_format():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    assert live[0]["clock"] == "00:00"
    # every clock is mm:ss with 2-digit fields
    for f in live:
        mm, ss = f["clock"].split(":")
        assert len(mm) == 2 and len(ss) == 2


def test_score_is_monotonic_and_matches_final_at_end():
    b = _bundle()
    tl = build_timeline(b, pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    h = [f["score"][0] for f in live]
    a = [f["score"][1] for f in live]
    assert h == sorted(h) and a == sorted(a)
    final = b["match"]["fixture"]["final"]
    assert f"{live[-1]['score'][0]}-{live[-1]['score'][1]}" == final


def test_each_goal_has_exactly_one_goal_frame():
    b = _bundle()
    tl = build_timeline(b, pre=2.0, live=8.0, post=2.0)
    goal_events = [e for e in b["match"]["events"] if e["type"] == "goal"]
    goal_frames = [f for f in tl["frames"] if f.get("goal")]
    assert len(goal_frames) == len(goal_events)


def test_winprob_interpolated_and_normalized():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    for f in live:
        wp = f["winprob"]
        assert abs(wp["home"] + wp["draw"] + wp["away"] - 1.0) < 0.03


def test_motion_index_in_range():
    b = _bundle(frames=120)
    tl = build_timeline(b, pre=2.0, live=4.0, post=2.0)
    n = len(b["motion"])
    for f in tl["frames"]:
        if f["act"] == "live":
            assert 0 <= f["motion_index"] < n
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_timeline.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `tiktok/matchsim/timeline.py`:

```python
"""Align the match (minutes) to video frames (30fps) across three acts.

Emits a per-frame render schedule so goals, the accelerated clock, the score,
and the win-prob swing land on exact frames — the piece the renderer needs that
the raw bundle doesn't carry.
"""
FPS = 30
PRE_SECONDS = 5.0
LIVE_SECONDS = 40.0
POST_SECONDS = 6.0


def _interp_winprob(track, minute):
    """Linear-interpolate the win-prob track at a match-minute."""
    if minute <= track[0]["minute"]:
        p = track[0]
        return {"home": p["home"], "draw": p["draw"], "away": p["away"]}
    if minute >= track[-1]["minute"]:
        p = track[-1]
        return {"home": p["home"], "draw": p["draw"], "away": p["away"]}
    for i in range(1, len(track)):
        b = track[i]
        if b["minute"] >= minute:
            a = track[i - 1]
            span = b["minute"] - a["minute"]
            t = 0.0 if span == 0 else (minute - a["minute"]) / span
            return {k: a[k] + (b[k] - a[k]) * t for k in ("home", "draw", "away")}
    p = track[-1]
    return {"home": p["home"], "draw": p["draw"], "away": p["away"]}


def _clock(minute):
    total_seconds = int(round(minute * 60))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def build_timeline(bundle, fps=FPS, pre=PRE_SECONDS, live=LIVE_SECONDS,
                   post=POST_SECONDS):
    match = bundle["match"]
    motion = bundle["motion"]
    goals = [e for e in match["events"] if e["type"] == "goal"]
    winprob = match["winprob"]

    pre_n = round(pre * fps)
    live_n = round(live * fps)
    post_n = round(post * fps)
    total = pre_n + live_n + post_n

    frames = []

    # ---- Act 1: pre-match (KICK OFF IN 3..2..1) ----
    for i in range(pre_n):
        t = i / max(pre_n - 1, 1)
        countdown = max(1, 3 - int(t * 3.0 + 1e-9))
        frames.append({"act": "pre", "t": t, "countdown": countdown})

    # ---- Act 2: live sim (0'..90') ----
    live_start = len(frames)
    for i in range(live_n):
        t = i / max(live_n - 1, 1)
        minute = t * 90.0
        ch = sum(1 for g in goals if g["team"] == "home" and g["minute"] <= minute)
        ca = sum(1 for g in goals if g["team"] == "away" and g["minute"] <= minute)
        wp = _interp_winprob(winprob, minute)
        wp = {k: round(v, 4) for k, v in wp.items()}
        motion_index = round(t * (len(motion) - 1)) if motion else 0
        frames.append({
            "act": "live", "t": t, "minute": minute, "clock": _clock(minute),
            "score": [ch, ca], "winprob": wp, "motion_index": motion_index,
            "goal": None,
        })

    # Mark the single live frame nearest each goal's minute as its goal-frame.
    live_frames = frames[live_start:live_start + live_n]
    for g in goals:
        best_i = min(range(len(live_frames)),
                     key=lambda k: abs(live_frames[k]["minute"] - g["minute"]))
        live_frames[best_i]["goal"] = g

    # ---- Act 3: full-time ----
    for i in range(post_n):
        t = i / max(post_n - 1, 1)
        frames.append({"act": "post", "t": t})

    return {
        "fps": fps, "total": total, "frames": frames,
        "acts": {
            "pre": (0, pre_n),
            "live": (pre_n, pre_n + live_n),
            "post": (pre_n + live_n, total),
        },
    }
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_timeline.py -v` → 8 passed.

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/timeline.py tiktok/matchsim/tests/test_timeline.py
git commit -m "feat(matchsim): frame timeline (minute/clock/score/winprob/goal alignment)"
```

---

### Task 3: Live-frame layout zones

**Files:**
- Create: `tiktok/matchsim/layout.py`
- Test: `tiktok/matchsim/tests/test_layout.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_layout.py`:

```python
from layout import live_zones, W, H


def test_canvas_constants():
    assert (W, H) == (1080, 1920)


def test_zones_present():
    z = live_zones()
    for key in ("header", "scoreboard", "progress", "winprob", "arena", "caption"):
        assert key in z


def test_bands_stack_without_overlap_and_in_canvas():
    z = live_zones()
    bands = [z["header"], z["scoreboard"], z["progress"], z["winprob"], z["caption"]]
    # each band is (x, y, w, h); all within canvas
    for (x, y, w, h) in bands:
        assert 0 <= x and 0 <= y
        assert x + w <= W and y + h <= H
    # vertical order header -> scoreboard -> progress -> winprob (top to bottom)
    order = [z["header"], z["scoreboard"], z["progress"], z["winprob"]]
    tops = [b[1] for b in order]
    assert tops == sorted(tops)
    for a, b in zip(order, order[1:]):
        assert a[1] + a[3] <= b[1] + 1  # no vertical overlap (1px tolerance)


def test_arena_circle_inside_canvas():
    z = live_zones()
    cx, cy, r = z["arena"]
    assert r > 0
    assert cx - r >= 0 and cx + r <= W
    assert cy - r >= 0 and cy + r <= H
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_layout.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `tiktok/matchsim/layout.py`:

```python
"""Zone geometry for the live-sim frame (1080x1920). Pure — returns rectangles
and the arena circle so drawing code never hard-codes coordinates.

Rect convention: (x, y, w, h). Arena: (cx, cy, r).
"""
W, H = 1080, 1920
MARGIN = 64


def live_zones():
    header = (MARGIN, 40, W - 2 * MARGIN, 70)
    scoreboard = (MARGIN, 130, W - 2 * MARGIN, 130)
    progress = (MARGIN, 280, W - 2 * MARGIN, 14)
    winprob = (MARGIN, 320, W - 2 * MARGIN, 90)

    arena_top = 470
    arena_bottom = H - 250
    r = min((W - 2 * MARGIN) // 2, (arena_bottom - arena_top) // 2)
    cx = W // 2
    cy = arena_top + r

    caption = (MARGIN, H - 210, W - 2 * MARGIN, 90)
    return {
        "header": header, "scoreboard": scoreboard, "progress": progress,
        "winprob": winprob, "arena": (cx, cy, r), "caption": caption,
    }
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_layout.py -v` → 4 passed.

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/layout.py tiktok/matchsim/tests/test_layout.py
git commit -m "feat(matchsim): live-frame layout zones"
```

---

### Task 4: Pillow draw primitives

**Files:**
- Create: `tiktok/matchsim/draw.py`
- Test: `tiktok/matchsim/tests/test_draw.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_draw.py`:

```python
from PIL import Image
import draw


def test_font_loads():
    f = draw.font("Anton.ttf", 48)
    assert f.size == 48


def test_gradient_bg_size():
    img = draw.gradient_bg(["#0b1030", "#131a48", "#080b24"], 1080, 1920)
    assert img.size == (1080, 1920)
    assert img.mode == "RGBA"


def test_orb_is_square_rgba_and_has_opaque_center():
    orb = draw.orb(120, "#DA020E", "MUN")
    assert orb.size == (120, 120)
    assert orb.mode == "RGBA"
    # center pixel is opaque (the disc fills the middle)
    assert orb.getpixel((60, 60))[3] == 255
    # a far corner is transparent (outside the circle)
    assert orb.getpixel((2, 2))[3] == 0


def test_text_layer_nonempty():
    layer = draw.text_layer("GOAL", draw.font("Anton.ttf", 60), (255, 255, 255))
    assert layer.mode == "RGBA"
    assert layer.size[0] > 0 and layer.size[1] > 0


def test_winprob_bar_size_and_opaque():
    bar = draw.winprob_bar(600, 40, 0.5, 0.3, 0.2,
                           "#DA020E", "#5a5a5a", "#cccccc")
    assert bar.size == (600, 40)
    # somewhere along the bar is opaque
    assert bar.getpixel((10, 20))[3] == 255


def test_glass_panel_size():
    p = draw.glass_panel(400, 200, radius=16)
    assert p.size == (400, 200)
    assert p.mode == "RGBA"
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_draw.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `tiktok/matchsim/draw.py`:

```python
"""Pillow drawing primitives for the MatchSim renderer, in the brand style of
make_video.py (Anton/Bebas fonts, gradients, glossy orbs, glass panels).
All functions return RGBA Images; the renderer composites them.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from colors import hex_to_rgb, lerp_rgb

FONTS = Path(__file__).resolve().parents[2] / "branding" / "fonts"

_font_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONTS / name), size)
    return _font_cache[key]


def gradient_bg(stops, w, h):
    """Vertical 3-stop gradient as an RGBA image."""
    top, mid, bot = (hex_to_rgb(s) for s in stops)
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        if t < 0.5:
            col = lerp_rgb(top, mid, t / 0.5)
        else:
            col = lerp_rgb(mid, bot, (t - 0.5) / 0.5)
        row = (*col, 255)
        for x in range(w):
            px[x, y] = row
    return img


def text_layer(text, fnt, fill, shadow=3):
    asc, desc = fnt.getmetrics()
    w = int(math.ceil(fnt.getlength(text)))
    h = asc + desc
    pad = max(6, shadow + 4)
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((pad + shadow, pad + shadow), text, font=fnt, fill=(0, 0, 0, 150))
    d.text((pad, pad), text, font=fnt, fill=(*fill, 255) if len(fill) == 3 else fill)
    return img


_orb_cache = {}


def orb(size, color_hex, monogram, mono_font="Anton.ttf"):
    """Glossy 3-D-looking disc: radial highlight -> colour -> shadow, plus a
    rim ring and a centered monogram. Cached by (size, colour, monogram) — the
    same disc is drawn on every frame, so building it once is essential.
    Callers only composite (read) the result, so sharing the cached image is safe.
    """
    ckey = (size, color_hex, monogram, mono_font)
    if ckey in _orb_cache:
        return _orb_cache[ckey]
    base = hex_to_rgb(color_hex)
    hi = lerp_rgb(base, (255, 255, 255), 0.55)
    lo = lerp_rgb(base, (0, 0, 0), 0.45)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    cx = cy = size / 2.0
    r = size / 2.0
    hx, hy = size * 0.35, size * 0.30  # highlight point
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r:
                continue
            d = math.hypot(x - hx, y - hy) / size
            t = min(1.0, d / 0.9)
            col = lerp_rgb(hi, base, t / 0.5) if t < 0.5 else lerp_rgb(base, lo, (t - 0.5) / 0.5)
            px[x, y] = (*col, 255)
    # rim ring
    d = ImageDraw.Draw(img)
    d.ellipse([1, 1, size - 2, size - 2], outline=(255, 255, 255, 90),
              width=max(2, size // 40))
    # monogram
    fsize = max(10, int(size * 0.30))
    while fsize > 8:
        f = font(mono_font, fsize)
        if f.getlength(monogram) <= size * 0.8:
            break
        fsize -= 2
    lab = text_layer(monogram, font(mono_font, fsize),
                     (255, 255, 255) if _luma(base) < 150 else (10, 14, 42))
    img.alpha_composite(lab, (int(cx - lab.width / 2), int(cy - lab.height / 2)))
    _orb_cache[ckey] = img
    return img


def _luma(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def glass_panel(w, h, radius=16, fill=(255, 255, 255, 18), outline=(245, 196, 81, 90)):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=fill,
                        outline=outline, width=2)
    return img


def winprob_bar(w, h, p_home, p_draw, p_away, c_home, c_draw, c_away):
    """Three-segment gradient bar with rounded ends."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    total = max(1e-6, p_home + p_draw + p_away)
    widths = [int(w * p_home / total), int(w * p_draw / total)]
    widths.append(w - sum(widths))
    cols = [hex_to_rgb(c_home), hex_to_rgb(c_draw), hex_to_rgb(c_away)]
    x = 0
    for seg_w, col in zip(widths, cols):
        top = lerp_rgb(col, (255, 255, 255), 0.25)
        for i in range(seg_w):
            tt = i / max(seg_w - 1, 1)
            c = lerp_rgb(top, col, tt)
            d.line([(x + i, 0), (x + i, h)], fill=(*c, 255))
        x += seg_w
    # rounded-corner mask
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1],
                                           radius=h // 2, fill=255)
    img.putalpha(mask)
    return img
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_draw.py -v` → 6 passed.

- [ ] **Step 5: Preview render (manual visual check).** Create nothing permanent — run this one-liner and eyeball the file:
```bash
python -c "import sys; sys.path.insert(0,'tiktok/matchsim'); import draw; from PIL import Image; bg=draw.gradient_bg(['#0b1030','#131a48','#080b24'],1080,1920); bg.alpha_composite(draw.orb(220,'#DA020E','MUN'),(120,700)); bg.alpha_composite(draw.orb(220,'#f4f4f4','RMA'),(740,700)); bg.alpha_composite(draw.winprob_bar(900,60,0.47,0.30,0.23,'#DA020E','#5a5a5a','#cccccc'),(90,400)); bg.convert('RGB').save('tiktok/output/_preview_draw.png')"
```
Open `tiktok/output/_preview_draw.png`: two glossy orbs (red MUN, white RMA) on a navy gradient with a three-segment win-prob bar. (`tiktok/output/` is gitignored.)

- [ ] **Step 6: Commit**
```bash
git add tiktok/matchsim/draw.py tiktok/matchsim/tests/test_draw.py
git commit -m "feat(matchsim): Pillow draw primitives (orbs, gradient, glass, winprob bar)"
```

---

### Task 5: Three-act frame renderer

**Files:**
- Create: `tiktok/matchsim/render_match.py`
- Test: `tiktok/matchsim/tests/test_render_match.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_render_match.py`:

```python
from pathlib import Path
from PIL import Image
from engine import simulate
from prepare import prepare
from timeline import build_timeline
from render_match import render_frames


def _tl_and_bundle():
    b = prepare(simulate("MUN", "RMA", competition="ucl", seed=21), n_frames=90)
    tl = build_timeline(b, pre=1.0, live=2.0, post=1.0)  # small: 30+60+30 = 120
    return b, tl


def test_writes_one_png_per_timeline_frame(tmp_path):
    b, tl = _tl_and_bundle()
    paths = render_frames(b, tl, tmp_path)
    assert len(paths) == tl["total"]
    assert all(Path(p).exists() for p in paths)


def test_frames_are_full_canvas(tmp_path):
    b, tl = _tl_and_bundle()
    paths = render_frames(b, tl, tmp_path)
    for p in (paths[0], paths[len(paths) // 2], paths[-1]):  # pre, live, post
        with Image.open(p) as im:
            assert im.size == (1080, 1920)


def test_deterministic_first_frame_bytes(tmp_path):
    b, tl = _tl_and_bundle()
    p1 = render_frames(b, tl, tmp_path / "a")
    p2 = render_frames(b, tl, tmp_path / "b")
    assert Path(p1[0]).read_bytes() == Path(p2[0]).read_bytes()
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_render_match.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement** — `tiktok/matchsim/render_match.py`:

```python
"""Compose the three acts into a PNG frame sequence driven by the timeline.

Act 1 pre-match: competition lockup, KICK OFF IN countdown, two orbs + VS.
Act 2 live: header, scoreboard, clock progress, win-prob bar, arena (orbs+ball),
            arcade caption on clash/goal frames.
Act 3 full-time: FULL TIME, big score, winner highlight, analytics panel.

Visual polish (goal replay/tracer/confetti, SFX, ticker scroll) is Plan 4.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import draw
import layout
import captions
from colors import hex_to_rgb, lerp_rgb

W, H = layout.W, layout.H

_bg_cache = {}


def _bg(theme):
    """Gradient background + vignette, cached by the theme's bg stops. The
    O(W*H) gradient is built once, not per frame; callers must .copy() before
    drawing so the shared cached image is never mutated."""
    key = tuple(theme["bg"])
    if key not in _bg_cache:
        img = draw.gradient_bg(theme["bg"], W, H)
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(v).rectangle([0, H - 320, W, H], fill=(0, 0, 0, 90))
        img.alpha_composite(v.filter(ImageFilter.GaussianBlur(60)))
        _bg_cache[key] = img
    return _bg_cache[key]


def _center(img, layer, cx, y):
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(y)))


def _acc(theme):
    return hex_to_rgb(theme["accent"])


def _pre_frame(bundle, fr):
    theme, fx = bundle["theme"], bundle["match"]["fixture"]
    img = _bg(theme).copy()
    d = ImageDraw.Draw(img)
    # competition lockup
    _center(img, draw.text_layer(theme["name"].upper(), draw.font("BebasNeue.ttf", 46),
                                 hex_to_rgb(theme["muted"])), W / 2, 120)
    # KICK OFF IN <n>
    _center(img, draw.text_layer(f"KICK OFF IN  {fr['countdown']}",
                                 draw.font("BebasNeue.ttf", 56), _acc(theme)), W / 2, 300)
    # orbs + VS
    _center(img, draw.orb(300, fx["home"]["color"], fx["home"]["monogram"]),
            W * 0.27, 560)
    _center(img, draw.orb(300, fx["away"]["color"], fx["away"]["monogram"]),
            W * 0.73, 560)
    _center(img, draw.text_layer("VS", draw.font("Anton.ttf", 130),
                                 (255, 255, 255)), W / 2, 620)
    _center(img, draw.text_layer(fx["home"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.27, 900)
    _center(img, draw.text_layer(fx["away"]["name"].upper(), draw.font("Anton.ttf", 54),
                                 (255, 255, 255)), W * 0.73, 900)
    _center(img, draw.text_layer(f"{theme['name'].upper()}  -  {fx['stage'].upper()}",
                                 draw.font("BebasNeue.ttf", 40),
                                 hex_to_rgb(theme["muted"])), W / 2, 1040)
    return img


def _arena(img, bundle, motion_frame, cx, cy, r, theme):
    fx = bundle["match"]["fixture"]
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ring)
    acc = _acc(theme)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*acc, 255), width=8)
    glow = ring.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow)
    img.alpha_composite(ring)

    def place(norm, size, disc):
        ox = cx + norm[0] * (r - size / 2)
        oy = cy - norm[1] * (r - size / 2)
        _center(img, disc, ox, oy - size / 2)

    disc_size = int(r * 0.42)
    place(motion_frame["home"], disc_size,
          draw.orb(disc_size, fx["home"]["color"], fx["home"]["monogram"]))
    place(motion_frame["away"], disc_size,
          draw.orb(disc_size, fx["away"]["color"], fx["away"]["monogram"]))
    # ball
    bx = cx + motion_frame["ball"][0] * r
    by = cy - motion_frame["ball"][1] * r
    ImageDraw.Draw(img).ellipse([bx - 9, by - 9, bx + 9, by + 9],
                                fill=(255, 255, 255, 255))


def _live_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    z = layout.live_zones()
    img = _bg(theme).copy()
    d = ImageDraw.Draw(img)

    # header: account left, LIVE right
    hx, hy, hw, hh = z["header"]
    img.alpha_composite(draw.text_layer("THE RED MANCUNIAN",
                        draw.font("BebasNeue.ttf", 34), hex_to_rgb(theme["text"])), (hx, hy))
    live = draw.text_layer("LIVE", draw.font("BebasNeue.ttf", 34), (255, 255, 255))
    img.alpha_composite(live, (hx + hw - live.width, hy))

    # scoreboard: clock tile + MON s - s RMA
    sx, sy, sw, sh = z["scoreboard"]
    clock = fr["clock"]
    tile = draw.font("Anton.ttf", 56)
    ct = draw.text_layer(clock, tile, (10, 14, 42))
    d.rounded_rectangle([sx, sy + 20, sx + ct.width + 40, sy + 20 + ct.height + 20],
                        radius=12, fill=(255, 255, 255, 235))
    img.alpha_composite(ct, (sx + 20, sy + 30))
    score = f"{fr['score'][0]}  -  {fr['score'][1]}"
    st = draw.text_layer(score, draw.font("Anton.ttf", 66), (255, 255, 255))
    _center(img, st, W / 2 + 120, sy + 20)
    _center(img, draw.text_layer(fx["home"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["home"]["color"])), W / 2 - 40, sy + 35)
    _center(img, draw.text_layer(fx["away"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["away"]["color"])), W / 2 + 280, sy + 35)

    # clock progress bar
    px, py, pw, ph = z["progress"]
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(255, 255, 255, 40))
    fillw = int(pw * fr["t"])
    if fillw > ph:
        d.rounded_rectangle([px, py, px + fillw, py + ph], radius=ph // 2,
                            fill=(*_acc(theme), 255))

    # win-prob bar
    wx, wy, ww, wh = z["winprob"]
    img.alpha_composite(draw.text_layer("LIVE WIN PROBABILITY - DIXON-COLES",
                        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["gold"])), (wx, wy))
    wp = fr["winprob"]
    bar = draw.winprob_bar(ww, 46, wp["home"], wp["draw"], wp["away"],
                           fx["home"]["color"], "#5a5a5a", fx["away"]["color"])
    img.alpha_composite(bar, (wx, wy + 40))

    # arena
    cx, cy, r = z["arena"]
    mi = fr["motion_index"]
    _arena(img, bundle, bundle["motion"][mi], cx, cy, r, theme)

    # arcade caption on clash or goal frames
    caption_text = None
    if fr.get("goal"):
        caption_text = captions.caption_for(fr["goal"], fx["seed"], fr["score"][0] + fr["score"][1])
    elif bundle["motion"][mi]["clash"]:
        caption_text = captions.caption_for({"type": "near_miss", "flavour": "clash"},
                                            fx["seed"], mi)
    if caption_text:
        cxr, cyr, cwr, chr_ = z["caption"]
        pill = draw.text_layer(caption_text, draw.font("Anton.ttf", 54), (255, 255, 255))
        _center(img, pill, W / 2, cyr)
    return img


def _post_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    an = match["analytics"]
    img = _bg(theme).copy()
    _center(img, draw.text_layer("FULL TIME", draw.font("BebasNeue.ttf", 52),
            _acc(theme)), W / 2, 150)
    sh, sa = (int(x) for x in fx["final"].split("-"))
    _center(img, draw.orb(240, fx["home"]["color"], fx["home"]["monogram"]), W * 0.24, 300)
    _center(img, draw.orb(240, fx["away"]["color"], fx["away"]["monogram"]), W * 0.76, 300)
    _center(img, draw.text_layer(f"{sh} : {sa}", draw.font("Anton.ttf", 150),
            (255, 255, 255)), W / 2, 330)
    winner = fx["home"]["name"] if sh > sa else (fx["away"]["name"] if sa > sh else None)
    if winner:
        _center(img, draw.text_layer(f"{winner.upper()} WIN", draw.font("Anton.ttf", 56),
                hex_to_rgb(theme["gold"])), W / 2, 600)
    # analytics panel
    panel = draw.glass_panel(W - 160, 520, radius=20)
    img.alpha_composite(panel, (80, 760))
    rows = [("POSSESSION", an["possession"]), ("SHOTS", an["shots"]),
            ("xG", an["xg"])]
    y = 820
    for label, (hv, av) in rows:
        _center(img, draw.text_layer(str(hv), draw.font("Anton.ttf", 52), (255, 255, 255)),
                240, y)
        _center(img, draw.text_layer(label, draw.font("BebasNeue.ttf", 34),
                hex_to_rgb(theme["muted"])), W / 2, y + 12)
        _center(img, draw.text_layer(str(av), draw.font("Anton.ttf", 52), (255, 255, 255)),
                W - 240, y)
        y += 130
    return img


def render_frames(bundle, timeline, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, fr in enumerate(timeline["frames"]):
        if fr["act"] == "pre":
            img = _pre_frame(bundle, fr)
        elif fr["act"] == "live":
            img = _live_frame(bundle, fr)
        else:
            img = _post_frame(bundle, fr)
        p = out_dir / f"f{i:05d}.png"
        img.convert("RGB").save(p)
        paths.append(str(p))
    return paths
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_render_match.py -v` → 3 passed. (This renders ~120 small frames; it may take 10–30s.)

- [ ] **Step 5: Preview render (manual visual check).** Render one frame from each act to eyeball:
```bash
python -c "import sys; sys.path.insert(0,'tiktok/matchsim'); from engine import simulate; from prepare import prepare; from timeline import build_timeline; import render_match as R; b=prepare(simulate('MUN','RMA',competition='ucl',seed=21),n_frames=300); tl=build_timeline(b); fr=tl['frames']; R._pre_frame(b,fr[10]).convert('RGB').save('tiktok/output/_prev_pre.png'); R._live_frame(b,fr[tl['acts']['live'][0]+300]).convert('RGB').save('tiktok/output/_prev_live.png'); R._post_frame(b,fr[-1]).convert('RGB').save('tiktok/output/_prev_post.png'); print('wrote 3 preview frames')"
```
Open `tiktok/output/_prev_pre.png`, `_prev_live.png`, `_prev_post.png` and confirm they resemble the approved mockup (pre-match hype, live arena with scoreboard + win-prob, full-time analytics). Note anything off for Plan 4 polish — do NOT block on pixel perfection here.

- [ ] **Step 6: Commit**
```bash
git add tiktok/matchsim/render_match.py tiktok/matchsim/tests/test_render_match.py
git commit -m "feat(matchsim): three-act frame renderer"
```

---

### Task 6: Encode + `render` CLI

**Files:**
- Create: `tiktok/matchsim/encode.py`
- Modify: `tiktok/matchsim/cli.py`
- Test: `tiktok/matchsim/tests/test_render_cli.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_render_cli.py`:

```python
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
    # reuse the channel's MP4 validator
    sys.path.insert(0, str(Path(CLI).resolve().parents[1].parent))  # tiktok/ on path
    import video
    assert video.validate_mp4(str(out)) == []
    # sidecar files
    assert out.with_name("match-caption.txt").exists()
    assert out.with_name("match-post-notes.txt").exists()


def test_render_help_lists_subcommand():
    r = subprocess.run([sys.executable, CLI, "--help"], capture_output=True, text=True)
    assert "render" in r.stdout
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_render_cli.py -v` → the `render` subcommand doesn't exist.

- [ ] **Step 3a: Implement the encoder** — `tiktok/matchsim/encode.py`:

```python
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
```

- [ ] **Step 3b: Add the `render` subcommand to `cli.py`.** Add imports near the others (`import prepare as prepare_mod` already exists from Plan 2):
```python
import timeline as timeline_mod
import render_match
import encode
import tempfile
```
Add the disclaimer constant near the top (after the imports):
```python
DISCLAIMER = "Unofficial fan content - not affiliated with any club or competition."
```
Add the handler next to `_cmd_prepare`:
```python
def _cmd_render(args):
    m = engine.simulate(
        args.home, args.away, competition=args.competition, seed=args.seed,
        home_xg=args.home_xg, away_xg=args.away_xg,
        venue=args.venue, stage=args.stage, date=args.date,
    )
    try:
        schema.validate(m)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    fps = 30
    n_frames = round((args.pre + args.live + args.post) * fps)
    bundle = prepare_mod.prepare(m, n_frames=n_frames)
    tl = timeline_mod.build_timeline(bundle, fps=fps, pre=args.pre,
                                     live=args.live, post=args.post)
    out_mp4 = Path(args.out)
    with tempfile.TemporaryDirectory() as td:
        render_match.render_frames(bundle, tl, td)
        encode.encode(td, out_mp4, fps=fps)
    fx = m["fixture"]
    caption = (f"{fx['home']['name']} {fx['final']} {fx['away']['name']} - "
               f"a {bundle['theme']['name']} simulation. Who wins the rematch? "
               f"Comment your scoreline. #matchsim #football\n{DISCLAIMER}")
    out_mp4.with_name(out_mp4.stem + "-caption.txt").write_text(caption, encoding="utf-8")
    notes = (f"POST PLAN - {fx['home']['name']} vs {fx['away']['name']}\n"
             f"1. Upload {out_mp4.name} to TikTok.\n"
             f"2. Add a trending sound at ~20% volume.\n"
             f"3. Paste the caption from {out_mp4.stem}-caption.txt.\n")
    out_mp4.with_name(out_mp4.stem + "-post-notes.txt").write_text(notes, encoding="utf-8")
    print(f"wrote {out_mp4}")
    return 0
```
Register the subparser in `main()` after the `prepare` block:
```python
    rp = sub.add_parser("render", help="simulate + render -> MP4 + caption + post-notes")
    rp.add_argument("--home", required=True)
    rp.add_argument("--away", required=True)
    rp.add_argument("--competition", default="generic")
    rp.add_argument("--seed", type=int, default=0)
    rp.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    rp.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    rp.add_argument("--venue", default="")
    rp.add_argument("--stage", default=None)
    rp.add_argument("--date", default="")
    rp.add_argument("--pre", type=float, default=5.0)
    rp.add_argument("--live", type=float, default=40.0)
    rp.add_argument("--post", type=float, default=6.0)
    rp.add_argument("--out", required=True)
    rp.set_defaults(func=_cmd_render)
```
Also add `from pathlib import Path` if not already imported (it is, from Plan 1).

- [ ] **Step 4: Run the render CLI test** — `python -m pytest tiktok/matchsim/tests/test_render_cli.py -v`
Expected: 2 passed (the MP4 test actually invokes ffmpeg — allow ~30–60s).

- [ ] **Step 5: Run the whole suite** — `python -m pytest tiktok/matchsim/tests/ -q`
Expected: all pass (Plans 1–3). The full render test is the slow one.

- [ ] **Step 6: Manual end-to-end** — render a real short clip and watch it:
```bash
python tiktok/matchsim/cli.py render --home MUN --away RMA --competition ucl --seed 21 --pre 3 --live 20 --post 5 --out tiktok/output/_matchsim_demo.mp4
```
Open `tiktok/output/_matchsim_demo.mp4`: ~28s, pre-match hype → live arena with moving/clashing orbs + live scoreboard + win-prob bar → full-time analytics. (gitignored.)

- [ ] **Step 7: Commit**
```bash
git add tiktok/matchsim/encode.py tiktok/matchsim/cli.py tiktok/matchsim/tests/test_render_cli.py
git commit -m "feat(matchsim): render CLI -> TikTok-safe MP4 + caption + post-notes"
```

---

## Self-Review

**Spec coverage (M3 + M4):**
- Three-act structure (pre-match / live / full-time) → Task 5 ✓ (spec §7)
- Premium visual language — brand fonts, glossy orbs, gradient bg, glass panel, gradient win-prob bar, glowing arena ring → Tasks 4–5 ✓ (baseline; heavy polish is Plan 4)
- Live Dixon-Coles win-prob bar + accelerated clock + progress bar → Task 5 ✓ (spec §8 mechanics 1–2)
- Arena-clash motion + arcade captions on clash/goal → Task 5 ✓
- Full-time analytics panel (possession/shots/xG) → Task 5 ✓
- Frame↔minute alignment (goals/clock/score/win-prob on exact frames) → Task 2 ✓ (the reviewer's carry-over)
- End-to-end `render` → MP4 + caption + post-notes (parity with render.py) → Task 6 ✓ (spec §5/M4)
- TikTok-safe encode validated via `video.validate_mp4` → Task 6 ✓
- Out of Plan-3 scope (Plan 4): goal replay slow-mo/tracer/confetti, SFX mux, batch, crest drop-in, ticker scroll, momentum meter, per-competition visual QA.

**Placeholder scan:** none — every code step is complete. Pixel-drawing tasks (4–5) pair smoke tests with explicit preview-render steps for visual sign-off, since pixel values can't be asserted meaningfully.

**Type/name consistency:** `build_timeline(bundle, fps, pre, live, post)` returns `{fps,total,frames,acts}` with per-frame keys `act/t` and live-only `minute/clock/score/winprob/motion_index/goal` — consumed exactly that way in `render_match._live_frame`. `layout.live_zones()` returns the keys `header/scoreboard/progress/winprob/arena/caption` used in `_live_frame`; `arena` is `(cx,cy,r)`. `draw.font/gradient_bg/text_layer/orb/glass_panel/winprob_bar` signatures match their call sites and tests. `render_frames(bundle, timeline, out_dir)` → list of PNG paths, consumed by the CLI via a temp dir then `encode.encode(frames_dir, out_mp4, fps)`. `captions.caption_for(event, seed, index)` and `colors.hex_to_rgb/lerp_rgb` reused from Plans 1–2 with their real signatures.

**Determinism:** the renderer is a pure function of the bundle + timeline (no RNG), so `test_deterministic_first_frame_bytes` holds; the bundle itself is already seed-deterministic from Plans 1–2.

**Performance note:** `draw.orb` and `draw.gradient_bg` are O(size²)/O(W·H) pure-Python pixel loops, so the plan **builds caching in from the start**: `draw.orb` memoizes by `(size, colour, monogram)` (Task 4) and `render_match._bg` memoizes the gradient+vignette by the theme's bg stops (Task 5), with act functions drawing on a `.copy()`. This turns the two most expensive operations from per-frame into once-per-render, which is what makes the Task 6 ffmpeg test and a full-length render complete in reasonable time (NFR1). Any further static-layer caching (scoreboard tile, panels) is a Plan 4 optimization.
```
