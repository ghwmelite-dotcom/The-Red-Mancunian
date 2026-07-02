# MatchSim Polish + Batch Implementation Plan (Plan 4 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the working three-act renderer (Plan 3) from "watchable" to "premium and postable at scale": win-prob % labels + swing callout, symmetric TikTok-title-safe HUD, arena disc glow, goal flash + confetti, full-time fade-in, SFX (whoosh transitions + goal accents), and batch rendering — plus competition-specific hashtags.

**Architecture:** Pure/testable first — extend `timeline.py` with the win-prob swing delta on goal frames, and `layout.py` with a title-safe header + symmetric scoreboard anchors. Add glow/confetti primitives to `draw.py`. Then apply visual polish inside `render_match.py` (smoke + preview). Then extend `encode.py` to mux SFX at act transitions and goals (reusing `tiktok/assets/whoosh.wav`), wired through `cli.py`. Finally add a `batch` subcommand and competition hashtags.

**Tech Stack:** Python 3, Pillow, ffmpeg/ffprobe, `pytest`. No new dependencies (SFX reuses the existing `whoosh.wav`).

**Spec:** `docs/superpowers/specs/2026-07-01-matchsim-design.md` (milestones M5–M7). Plans 1–3 (engine, data layer, renderer) are on this branch.

**Conventions (unchanged):** `tiktok/matchsim/` plain module dir (NO `__init__.py`); bare imports; `tests/conftest.py` on `sys.path`; run from repo root `C:\dev\Projects\The-Red-Mancunian`; renderer is a pure function of the bundle+timeline.

**Explicitly deferred (future, NOT this plan):** full slow-mo goal *replay* sub-sequences with ball-path tracer (needs timeline restructuring); animated ticker scroll; crest-image drop-in; momentum meter; per-competition visual QA sweep. These are noted so they are not treated as gaps.

**Current state the tasks build on (verify by reading):**
- `timeline.build_timeline(bundle, fps, pre, live, post)` → `{fps,total,frames,acts}`; live frames have `act/t/minute/clock/score/winprob/motion_index/goal`.
- `layout.live_zones()` → `header/scoreboard/progress/winprob/arena/caption` (rects; arena is `(cx,cy,r)`), plus `W,H,MARGIN`.
- `draw`: `font/gradient_bg/text_layer/orb/glass_panel/winprob_bar`, module caches `_font_cache/_orb_cache`.
- `render_match`: `_bg(theme)` (cached), `_center/_acc/_pre_frame/_arena/_live_frame/_post_frame/render_frames`.
- `encode.encode(frames_dir, out_mp4, fps=30)` → silent-AAC MP4.
- `cli.py`: `simulate/prepare/render` subcommands; `_cmd_render` uses a tempdir + `encode.encode`.
- `tiktok/assets/whoosh.wav` exists (reused by the news pipeline).

---

### Task 1: Win-prob swing on goal frames

**Files:**
- Modify: `tiktok/matchsim/timeline.py`
- Test: `tiktok/matchsim/tests/test_timeline_swing.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_timeline_swing.py`:

```python
from timeline import build_timeline


def _bundle_with_goal():
    # synthetic bundle: one home goal at 30' where the track jumps for home
    return {
        "match": {
            "events": [
                {"minute": 30, "type": "goal", "team": "home", "scorer": "A",
                 "scoreAfter": "1-0"},
                {"minute": 90, "type": "full_time", "scoreAfter": "1-0"},
            ],
            "winprob": [
                {"minute": 0, "home": 0.50, "draw": 0.30, "away": 0.20},
                {"minute": 30, "home": 0.72, "draw": 0.18, "away": 0.10},
                {"minute": 90, "home": 1.0, "draw": 0.0, "away": 0.0},
            ],
            "fixture": {"final": "1-0"},
        },
        "motion": [{"home": [0, 0], "away": [0, 0], "ball": [0, 0], "clash": False}] * 60,
    }


def test_goal_frame_has_swing_with_team_and_delta():
    tl = build_timeline(_bundle_with_goal(), pre=1.0, live=4.0, post=1.0)
    goal_frames = [f for f in tl["frames"] if f.get("goal")]
    assert len(goal_frames) == 1
    sw = goal_frames[0]["swing"]
    assert sw["team"] == "home"
    # home jumped 0.50 -> 0.72 across the goal = +22 points
    assert sw["delta"] == 22


def test_non_goal_live_frames_have_no_swing():
    tl = build_timeline(_bundle_with_goal(), pre=1.0, live=4.0, post=1.0)
    non_goal_live = [f for f in tl["frames"]
                     if f["act"] == "live" and not f.get("goal")]
    assert all("swing" not in f for f in non_goal_live)
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_timeline_swing.py -v` → FAIL (`KeyError: 'swing'`).

- [ ] **Step 3: Implement.** In `tiktok/matchsim/timeline.py`, in `build_timeline`, immediately AFTER the goal-frame assignment block (the loop that sets `live_frames[k]["goal"] = g`) and BEFORE the `# ---- Act 3` comment, add:

```python
    # Win-prob swing on each goal frame: the scoring side's jump at that goal.
    for g in goals:
        idx = next((i for i, p in enumerate(winprob) if p["minute"] == g["minute"]), None)
        if idx is None or idx == 0:
            continue
        delta = round((winprob[idx][g["team"]] - winprob[idx - 1][g["team"]]) * 100)
        for f in live_frames:
            if f.get("goal") is g:
                f["swing"] = {"team": g["team"], "delta": delta}
                break
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_timeline_swing.py -v` → 2 passed. Then `python -m pytest tiktok/matchsim/tests/test_timeline.py tiktok/matchsim/tests/test_timeline_swing.py -q` → all pass (no regression).

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/timeline.py tiktok/matchsim/tests/test_timeline_swing.py
git commit -m "feat(matchsim): win-prob swing delta on goal frames"
```

---

### Task 2: Title-safe header + symmetric scoreboard anchors

**Files:**
- Modify: `tiktok/matchsim/layout.py`
- Test: `tiktok/matchsim/tests/test_layout_safe.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_layout_safe.py`:

```python
from layout import live_zones, W


def test_header_below_tiktok_top_ui():
    z = live_zones()
    _, hy, _, _ = z["header"]
    assert hy >= 80  # clear of the TikTok top status/nav area


def test_score_anchors_symmetric_about_centre():
    z = live_zones()
    home_x, score_x, away_x = z["score_anchors"]
    assert score_x == W // 2
    assert W // 2 - home_x == away_x - W // 2  # equal offsets
    assert home_x < score_x < away_x
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_layout_safe.py -v` → FAIL (header y is 40; `score_anchors` missing).

- [ ] **Step 3: Implement.** In `tiktok/matchsim/layout.py`, edit `live_zones()`:
  (a) change the header line from `header = (MARGIN, 40, W - 2 * MARGIN, 70)` to:
```python
    header = (MARGIN, 96, W - 2 * MARGIN, 70)
```
  (b) shift the bands below it down by 56 so they don't collide with the lower header — change these three lines:
```python
    scoreboard = (MARGIN, 130, W - 2 * MARGIN, 130)
    progress = (MARGIN, 280, W - 2 * MARGIN, 14)
    winprob = (MARGIN, 320, W - 2 * MARGIN, 90)
```
  to:
```python
    scoreboard = (MARGIN, 186, W - 2 * MARGIN, 130)
    progress = (MARGIN, 336, W - 2 * MARGIN, 14)
    winprob = (MARGIN, 376, W - 2 * MARGIN, 96)
```
  (c) lower the arena top to make room — change `arena_top = 470` to:
```python
    arena_top = 540
```
  (d) add symmetric score anchors and include them in the returned dict. Before the `return`, add:
```python
    score_anchors = (W // 2 - 210, W // 2, W // 2 + 210)
```
  and add `"score_anchors": score_anchors,` to the returned dict.

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_layout_safe.py tiktok/matchsim/tests/test_layout.py -v` → all pass (the original layout tests still hold: bands still stack, arena still inside canvas).

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/layout.py tiktok/matchsim/tests/test_layout_safe.py
git commit -m "feat(matchsim): title-safe header + symmetric scoreboard anchors"
```

---

### Task 3: Glow + confetti draw primitives

**Files:**
- Modify: `tiktok/matchsim/draw.py`
- Test: `tiktok/matchsim/tests/test_draw_fx.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_draw_fx.py`:

```python
import draw


def test_halo_size_and_transparent_by_default():
    h = draw.halo(200, "#DA020E", blur=20)
    assert h.size == (200, 200)
    assert h.mode == "RGBA"
    # corner is (semi-)transparent — the glow fades out
    assert h.getpixel((1, 1))[3] < 255


def test_confetti_deterministic_and_sized():
    a = draw.confetti(400, 300, seed=7, n=60)
    b = draw.confetti(400, 300, seed=7, n=60)
    assert a.size == (400, 300)
    assert a.tobytes() == b.tobytes()  # same seed -> identical
    c = draw.confetti(400, 300, seed=8, n=60)
    assert c.tobytes() != a.tobytes()  # different seed -> differs


def test_confetti_actually_draws_particles():
    img = draw.confetti(200, 200, seed=1, n=120)
    # at least some pixels are non-transparent
    assert any(img.getpixel((x, y))[3] > 0
               for x in range(0, 200, 7) for y in range(0, 200, 7))
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_draw_fx.py -v` → FAIL (`AttributeError: module 'draw' has no attribute 'halo'`).

- [ ] **Step 3: Implement.** In `tiktok/matchsim/draw.py`:
  (a) change the import line `from PIL import Image, ImageDraw, ImageFont` to:
```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter
```
  (b) add `import random` at the top (next to `import math`).
  (c) append these two functions to the end of the file:
```python
def halo(size, color_hex, blur=20):
    """A soft circular glow (for the possessing disc / accents)."""
    base = hex_to_rgb(color_hex)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(2, size // 10)
    d.ellipse([pad, pad, size - pad, size - pad], fill=(*base, 200))
    return img.filter(ImageFilter.GaussianBlur(blur))


def confetti(w, h, seed, n=80, colors=None):
    """Deterministic scatter of small confetti rectangles (goal celebration)."""
    if colors is None:
        colors = [(255, 255, 255), (245, 196, 81), (218, 2, 14), (57, 230, 230)]
    rng = random.Random(seed * 2654435761 + 1)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        sw = rng.randint(4, 10)
        sh = rng.randint(6, 14)
        col = colors[rng.randrange(len(colors))]
        d.rectangle([x, y, x + sw, y + sh], fill=(*col, 235))
    return img
```

- [ ] **Step 4: Run to verify pass** — `python -m pytest tiktok/matchsim/tests/test_draw_fx.py tiktok/matchsim/tests/test_draw.py -v` → all pass.

- [ ] **Step 5: Commit**
```bash
git add tiktok/matchsim/draw.py tiktok/matchsim/tests/test_draw_fx.py
git commit -m "feat(matchsim): halo + confetti draw primitives"
```

---

### Task 4: Live-HUD polish (safe header, symmetric scoreboard, win-prob labels + swing)

**Files:**
- Modify: `tiktok/matchsim/render_match.py`
- Test: `tiktok/matchsim/tests/test_render_match.py` (existing smoke tests must still pass)

- [ ] **Step 1: Replace `_live_frame`** in `tiktok/matchsim/render_match.py` with this version (uses the symmetric anchors, draws win-prob % labels + the swing callout, and keeps the arena/caption logic):

```python
def _live_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    z = layout.live_zones()
    img = _bg(theme).copy()
    d = ImageDraw.Draw(img)

    hx, hy, hw, hh = z["header"]
    img.alpha_composite(draw.text_layer("THE RED MANCUNIAN",
                        draw.font("BebasNeue.ttf", 34), hex_to_rgb(theme["text"])), (hx, hy))
    livelbl = draw.text_layer("LIVE", draw.font("BebasNeue.ttf", 34), (255, 80, 80))
    img.alpha_composite(livelbl, (hx + hw - livelbl.width, hy))

    sx, sy, sw, sh = z["scoreboard"]
    home_x, score_x, away_x = z["score_anchors"]
    ct = draw.text_layer(fr["clock"], draw.font("Anton.ttf", 52), (10, 14, 42))
    d.rounded_rectangle([sx, sy + 24, sx + ct.width + 40, sy + 24 + ct.height + 18],
                        radius=12, fill=(255, 255, 255, 235))
    img.alpha_composite(ct, (sx + 20, sy + 32))
    _center(img, draw.text_layer(fx["home"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["home"]["color"])), home_x, sy + 44)
    _center(img, draw.text_layer(f"{fr['score'][0]}  -  {fr['score'][1]}",
            draw.font("Anton.ttf", 66), (255, 255, 255)), score_x, sy + 28)
    _center(img, draw.text_layer(fx["away"]["monogram"], draw.font("Anton.ttf", 40),
            hex_to_rgb(fx["away"]["color"])), away_x, sy + 44)

    px, py, pw, ph = z["progress"]
    d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(255, 255, 255, 40))
    fillw = int(pw * fr["t"])
    if fillw >= ph:
        d.rounded_rectangle([px, py, px + fillw, py + ph], radius=ph // 2,
                            fill=(*_acc(theme), 255))

    wx, wy, ww, wh = z["winprob"]
    img.alpha_composite(draw.text_layer("LIVE WIN PROBABILITY - DIXON-COLES",
                        draw.font("BebasNeue.ttf", 26), hex_to_rgb(theme["gold"])), (wx, wy))
    wp = fr["winprob"]
    bar_y = wy + 40
    bar = draw.winprob_bar(ww, 46, wp["home"], wp["draw"], wp["away"],
                           fx["home"]["color"], "#5a5a5a", fx["away"]["color"])
    img.alpha_composite(bar, (wx, bar_y))
    # percentage labels centred over each segment
    total = max(1e-6, wp["home"] + wp["draw"] + wp["away"])
    hw_ = ww * wp["home"] / total
    aw_ = ww * wp["away"] / total
    _center(img, draw.text_layer(f"{round(wp['home'] * 100)}%",
            draw.font("Anton.ttf", 26), (255, 255, 255)), wx + hw_ / 2, bar_y + 8)
    _center(img, draw.text_layer(f"{round(wp['away'] * 100)}%",
            draw.font("Anton.ttf", 26), (10, 14, 42)), wx + ww - aw_ / 2, bar_y + 8)
    # swing callout on goal frames
    if fr.get("swing"):
        sw_ = fr["swing"]
        who = fx[sw_["team"]]["monogram"]
        tag = draw.text_layer(f"UP {who} +{sw_['delta']}%",
                              draw.font("Anton.ttf", 30), (70, 220, 120))
        img.alpha_composite(tag, (wx + ww - tag.width, wy - 4))

    cx, cy, r = z["arena"]
    mi = fr["motion_index"]
    _arena(img, bundle, bundle["motion"][mi], cx, cy, r, theme)

    caption_text = None
    if fr.get("goal"):
        caption_text = captions.caption_for(fr["goal"], fx["seed"], fr["score"][0] + fr["score"][1])
    elif bundle["motion"][mi]["clash"]:
        caption_text = captions.caption_for({"type": "near_miss", "flavour": "clash"},
                                            fx["seed"], mi)
    if caption_text:
        cxr, cyr, cwr, chr_ = z["caption"]
        pill_font = draw.font("Anton.ttf", 54)
        tw = int(pill_font.getlength(caption_text))
        pill = draw.glass_panel(tw + 60, 84, radius=18,
                                fill=(10, 14, 42, 180), outline=(245, 196, 81, 200))
        _center(img, pill, W / 2, cyr)
        _center(img, draw.text_layer(caption_text, pill_font, (255, 255, 255)),
                W / 2, cyr + 10)
    return img
```

- [ ] **Step 2: Run the smoke tests** — `python -m pytest tiktok/matchsim/tests/test_render_match.py -v` → 3 passed (renders still succeed at 1080x1920, deterministic).

- [ ] **Step 3: Preview** — render a live frame that has a swing and a clash:
```bash
python -c "import sys; sys.path.insert(0,'tiktok/matchsim'); from engine import simulate; from prepare import prepare; from timeline import build_timeline; import render_match as R; b=prepare(simulate('MUN','RMA',competition='ucl',seed=21),n_frames=300); tl=build_timeline(b); goal=[f for f in tl['frames'] if f.get('goal')]; R._live_frame(b, goal[0] if goal else tl['frames'][200]).convert('RGB').save('tiktok/output/_polish_live.png'); print('wrote')"
```
Open `tiktok/output/_polish_live.png`: header sits lower (title-safe), scoreboard is symmetric, the win-prob bar has % labels, and (on a goal frame) an "UP <MON> +N%" green swing callout appears; captions sit on a glass pill. Report any layout collisions.

- [ ] **Step 4: Commit**
```bash
git add tiktok/matchsim/render_match.py
git commit -m "feat(matchsim): live HUD polish (safe header, symmetric scoreboard, winprob labels + swing)"
```

---

### Task 5: Arena glow, goal flash + confetti, full-time fade-in

**Files:**
- Modify: `tiktok/matchsim/render_match.py`
- Test: `tiktok/matchsim/tests/test_render_match.py` (smoke must still pass)

- [ ] **Step 1: Replace `_arena`** with a version that adds a glow halo behind the possessing disc (the one nearest the ball):

```python
def _arena(img, bundle, motion_frame, cx, cy, r, theme):
    fx = bundle["match"]["fixture"]
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ring)
    acc = _acc(theme)
    dd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*acc, 255), width=8)
    glow = ring.filter(ImageFilter.GaussianBlur(18))
    img.alpha_composite(glow)
    img.alpha_composite(ring)

    disc_size = int(r * 0.46)

    def screen(norm, size):
        return (cx + norm[0] * (r - size / 2), cy - norm[1] * (r - size / 2))

    # which disc is "in possession" = nearest the ball
    ball = motion_frame["ball"]
    dh = (motion_frame["home"][0] - ball[0]) ** 2 + (motion_frame["home"][1] - ball[1]) ** 2
    da = (motion_frame["away"][0] - ball[0]) ** 2 + (motion_frame["away"][1] - ball[1]) ** 2
    poss = "home" if dh <= da else "away"

    for side in ("home", "away"):
        ox, oy = screen(motion_frame[side], disc_size)
        if side == poss:
            hl = draw.halo(int(disc_size * 1.7), fx[side]["color"], blur=22)
            _center(img, hl, ox, oy)
        disc = draw.orb(disc_size, fx[side]["color"], fx[side]["monogram"])
        _center(img, disc, ox, oy)

    bx = cx + ball[0] * r
    by = cy - ball[1] * r
    ImageDraw.Draw(img).ellipse([bx - 9, by - 9, bx + 9, by + 9],
                                fill=(255, 255, 255, 255))
```

- [ ] **Step 2: Add a goal flash + confetti overlay to `_live_frame`.** In the `_live_frame` you edited in Task 4, insert this block immediately BEFORE the final `return img` line:

```python
    if fr.get("goal"):
        flash = Image.new("RGBA", (W, H), (255, 255, 255, 60))
        img.alpha_composite(flash)
        img.alpha_composite(draw.confetti(W, H, seed=fx["seed"] + fr["minute"], n=140),
                            (0, 0))
        _center(img, draw.text_layer("GOAL!", draw.font("Anton.ttf", 120),
                (255, 255, 255)), W / 2, cy - 40)
```
(`cy` is already defined earlier in `_live_frame` from `cx, cy, r = z["arena"]`.)

- [ ] **Step 3: Add a fade-in to `_post_frame`.** Replace `_post_frame` with a version that fades the whole card in using `fr["t"]`:

```python
def _post_frame(bundle, fr):
    theme, match = bundle["theme"], bundle["match"]
    fx = match["fixture"]
    an = match["analytics"]
    img = _bg(theme).copy()
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    _center(card, draw.text_layer("FULL TIME", draw.font("BebasNeue.ttf", 52),
            _acc(theme)), W / 2, 150)
    sh, sa = (int(x) for x in fx["final"].split("-"))
    _center(card, draw.orb(240, fx["home"]["color"], fx["home"]["monogram"]), W * 0.24, 300)
    _center(card, draw.orb(240, fx["away"]["color"], fx["away"]["monogram"]), W * 0.76, 300)
    _center(card, draw.text_layer(f"{sh} : {sa}", draw.font("Anton.ttf", 150),
            (255, 255, 255)), W / 2, 330)
    winner = fx["home"]["name"] if sh > sa else (fx["away"]["name"] if sa > sh else None)
    if winner:
        _center(card, draw.text_layer(f"{winner.upper()} WIN", draw.font("Anton.ttf", 56),
                hex_to_rgb(theme["gold"])), W / 2, 600)
    panel = draw.glass_panel(W - 160, 520, radius=20)
    card.alpha_composite(panel, (80, 760))
    rows = [("POSSESSION", an["possession"]), ("SHOTS", an["shots"]), ("xG", an["xg"])]
    y = 820
    for label, (hv, av) in rows:
        _center(card, draw.text_layer(str(hv), draw.font("Anton.ttf", 52), (255, 255, 255)),
                240, y)
        _center(card, draw.text_layer(label, draw.font("BebasNeue.ttf", 34),
                hex_to_rgb(theme["muted"])), W / 2, y + 12)
        _center(card, draw.text_layer(str(av), draw.font("Anton.ttf", 52), (255, 255, 255)),
                W - 240, y)
        y += 130
    # ease-in over the first ~35% of the act
    alpha = min(1.0, fr["t"] / 0.35)
    if alpha < 1.0:
        r_, g_, b_, a_ = card.split()
        card = Image.merge("RGBA", (r_, g_, b_, a_.point(lambda v: int(v * alpha))))
    img.alpha_composite(card)
    return img
```

- [ ] **Step 4: Run the smoke tests** — `python -m pytest tiktok/matchsim/tests/test_render_match.py -v` → 3 passed.

- [ ] **Step 5: Preview** — a goal frame and an early full-time frame:
```bash
python -c "import sys; sys.path.insert(0,'tiktok/matchsim'); from engine import simulate; from prepare import prepare; from timeline import build_timeline; import render_match as R; b=prepare(simulate('MUN','RMA',competition='ucl',seed=21),n_frames=300); tl=build_timeline(b); g=[f for f in tl['frames'] if f.get('goal')]; (g and R._live_frame(b,g[0]).convert('RGB').save('tiktok/output/_polish_goal.png')); post=[f for f in tl['frames'] if f['act']=='post']; R._post_frame(b,post[3]).convert('RGB').save('tiktok/output/_polish_post_fade.png'); print('wrote')"
```
Open `tiktok/output/_polish_goal.png` (white flash + confetti + big GOAL! + possessing-disc glow) and `_polish_post_fade.png` (full-time card partially faded in). Report any issues.

- [ ] **Step 6: Commit**
```bash
git add tiktok/matchsim/render_match.py
git commit -m "feat(matchsim): arena disc glow, goal flash + confetti, full-time fade-in"
```

---

### Task 6: SFX (whoosh transitions + goal accents)

**Files:**
- Modify: `tiktok/matchsim/encode.py`
- Modify: `tiktok/matchsim/cli.py`
- Test: `tiktok/matchsim/tests/test_encode_sfx.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_encode_sfx.py`:

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
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_encode_sfx.py -v`. NOTE: this may already PASS because the current encoder adds a silent AAC track. That is fine — this test guards that audio survives the SFX change. To make the SFX behaviour itself testable, ALSO confirm manually in Step 5 that the file is not silent. (If it passes now, proceed to implement SFX and keep it green.)

- [ ] **Step 3: Rewrite `encode.py`** to accept SFX events and mux the whoosh at each. Replace the whole file with:

```python
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
```

- [ ] **Step 4: Wire SFX events from the timeline in `cli.py`.** In `_cmd_render`, replace the encode block:
```python
    out_mp4 = Path(args.out)
    with tempfile.TemporaryDirectory() as td:
        render_match.render_frames(bundle, tl, td)
        encode.encode(td, out_mp4, fps=fps)
```
with:
```python
    out_mp4 = Path(args.out)
    sfx = []
    live_a, live_b = tl["acts"]["live"]
    post_a = tl["acts"]["post"][0]
    sfx.append((live_a / fps, 0.7))   # whoosh into the live act
    sfx.append((post_a / fps, 0.7))   # whoosh into full-time
    for i, fr in enumerate(tl["frames"]):
        if fr.get("goal"):
            sfx.append((i / fps, 1.0))  # louder accent on each goal
    with tempfile.TemporaryDirectory() as td:
        render_match.render_frames(bundle, tl, td)
        encode.encode(td, out_mp4, fps=fps, sfx_events=sfx)
```

- [ ] **Step 5: Run the SFX test + the render-cli test** — `python -m pytest tiktok/matchsim/tests/test_encode_sfx.py tiktok/matchsim/tests/test_render_cli.py -v` → all pass. Then verify the file is genuinely not silent (mean volume should be well above -91 dB):
```bash
python tiktok/matchsim/cli.py render --home MUN --away RMA --competition ucl --seed 21 --pre 2 --live 8 --post 3 --out tiktok/output/_sfx_demo.mp4
ffmpeg -hide_banner -i tiktok/output/_sfx_demo.mp4 -af volumedetect -f null - 2>&1 | grep -i mean_volume
```
Expected: a `mean_volume` well above the ~-91 dB of pure silence (there is audible whoosh/accent content). Report the value.

- [ ] **Step 6: Commit**
```bash
git add tiktok/matchsim/encode.py tiktok/matchsim/cli.py tiktok/matchsim/tests/test_encode_sfx.py
git commit -m "feat(matchsim): SFX - whoosh at act transitions + goal accents"
```

---

### Task 7: Batch mode + competition hashtags

**Files:**
- Modify: `tiktok/matchsim/cli.py`
- Test: `tiktok/matchsim/tests/test_batch.py`

- [ ] **Step 1: Write the failing test** — `tiktok/matchsim/tests/test_batch.py`:

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
        {"home": "ZZZ", "away": "RMA", "competition": "ucl", "seed": 2},  # unknown team
    ]
    fx_file = tmp_path / "fixtures.json"
    fx_file.write_text(json.dumps(fixtures), encoding="utf-8")
    out_dir = tmp_path / "out"
    r = subprocess.run(
        [sys.executable, CLI, "batch", "--fixtures", str(fx_file),
         "--out-dir", str(out_dir), "--pre", "1", "--live", "1", "--post", "1"],
        capture_output=True, text=True,
    )
    # the good fixture still renders; the bad one is skipped, run exits 0
    assert (out_dir / "mun-vs-rma.mp4").exists()
    assert not (out_dir / "zzz-vs-rma.mp4").exists()


def test_render_caption_includes_competition_hashtag(tmp_path):
    out = tmp_path / "m.mp4"
    # render is heavy; only run the ffmpeg path when available
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not installed")
    subprocess.run(
        [sys.executable, CLI, "render", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21",
         "--pre", "1", "--live", "1", "--post", "1", "--out", str(out)],
        capture_output=True, text=True, check=True,
    )
    caption = out.with_name("m-caption.txt").read_text(encoding="utf-8")
    assert "#ucl" in caption
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tiktok/matchsim/tests/test_batch.py -v` → FAIL (no `batch` subcommand; caption lacks `#ucl`).

- [ ] **Step 3: Add competition hashtags + refactor render into a reusable function, then add batch.** In `tiktok/matchsim/cli.py`:

  (a) add a hashtag map constant near `DISCLAIMER`:
```python
COMP_HASHTAG = {"ucl": "#ucl #championsleague", "epl": "#premierleague",
                "wc": "#worldcup", "generic": ""}
```

  (b) refactor the body of `_cmd_render` into a reusable `_render_one(...)` helper and have both `_cmd_render` and the new batch command call it. Add this function (place it above `_cmd_render`):
```python
def _render_one(home, away, competition, seed, out_mp4,
                home_xg=None, away_xg=None, venue="", stage=None, date="",
                pre=5.0, live=40.0, post=6.0, fps=30):
    m = engine.simulate(home, away, competition=competition, seed=seed,
                        home_xg=home_xg, away_xg=away_xg,
                        venue=venue, stage=stage, date=date)
    schema.validate(m)
    n_frames = round((pre + live + post) * fps)
    bundle = prepare_mod.prepare(m, n_frames=n_frames)
    tl = timeline_mod.build_timeline(bundle, fps=fps, pre=pre, live=live, post=post)
    out_mp4 = Path(out_mp4)
    sfx = []
    live_a = tl["acts"]["live"][0]
    post_a = tl["acts"]["post"][0]
    sfx.append((live_a / fps, 0.7))
    sfx.append((post_a / fps, 0.7))
    for i, fr in enumerate(tl["frames"]):
        if fr.get("goal"):
            sfx.append((i / fps, 1.0))
    with tempfile.TemporaryDirectory() as td:
        render_match.render_frames(bundle, tl, td)
        encode.encode(td, out_mp4, fps=fps, sfx_events=sfx)
    fx = m["fixture"]
    tags = COMP_HASHTAG.get(competition, "")
    caption = (f"{fx['home']['name']} {fx['final']} {fx['away']['name']} - "
               f"a {bundle['theme']['name']} simulation. Who wins the rematch? "
               f"Comment your scoreline. #matchsim #football {tags}\n{DISCLAIMER}")
    out_mp4.with_name(out_mp4.stem + "-caption.txt").write_text(caption, encoding="utf-8")
    notes = (f"POST PLAN - {fx['home']['name']} vs {fx['away']['name']}\n"
             f"1. Upload {out_mp4.name} to TikTok.\n"
             f"2. Add a trending sound at ~20% volume.\n"
             f"3. Paste the caption from {out_mp4.stem}-caption.txt.\n")
    out_mp4.with_name(out_mp4.stem + "-post-notes.txt").write_text(notes, encoding="utf-8")
    return out_mp4
```

  (c) replace the body of `_cmd_render` with a thin wrapper:
```python
def _cmd_render(args):
    try:
        out = _render_one(args.home, args.away, args.competition, args.seed, args.out,
                          home_xg=args.home_xg, away_xg=args.away_xg,
                          venue=args.venue, stage=args.stage, date=args.date,
                          pre=args.pre, live=args.live, post=args.post)
    except schema.SchemaError as e:
        print(f"schema error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {out}")
    return 0
```

  (d) add the batch handler (next to `_cmd_render`):
```python
def _cmd_batch(args):
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ok, failed = 0, 0
    for fxt in fixtures:
        home, away = fxt["home"], fxt["away"]
        name = f"{home}-vs-{away}".lower()
        out_mp4 = out_dir / f"{name}.mp4"
        try:
            _render_one(home, away, fxt.get("competition", "generic"),
                        int(fxt.get("seed", 0)), out_mp4,
                        pre=args.pre, live=args.live, post=args.post)
            print(f"ok   {out_mp4.name}")
            ok += 1
        except Exception as e:  # isolate: one bad fixture must not halt the batch
            print(f"FAIL {name}: {e}", file=sys.stderr)
            failed += 1
    print(f"batch done: {ok} ok, {failed} failed")
    return 0
```

  (e) register the `batch` subparser in `main()` after the `render` block:
```python
    bp = sub.add_parser("batch", help="render a JSON list of fixtures -> a directory of MP4s")
    bp.add_argument("--fixtures", required=True, help="JSON list of {home,away,competition?,seed?}")
    bp.add_argument("--out-dir", required=True, dest="out_dir")
    bp.add_argument("--pre", type=float, default=5.0)
    bp.add_argument("--live", type=float, default=40.0)
    bp.add_argument("--post", type=float, default=6.0)
    bp.set_defaults(func=_cmd_batch)
```

- [ ] **Step 4: Run the batch test + render-cli regression** — `python -m pytest tiktok/matchsim/tests/test_batch.py tiktok/matchsim/tests/test_render_cli.py -v` → all pass.

- [ ] **Step 5: Run the whole suite** — `python -m pytest tiktok/matchsim/tests/ -q` → all pass (this includes several ffmpeg renders — be patient, several minutes).

- [ ] **Step 6: End-to-end batch demo:**
```bash
printf '[{"home":"MUN","away":"LIV","competition":"epl","seed":5},{"home":"MUN","away":"RMA","competition":"ucl","seed":9}]' > tiktok/output/_fixtures.json
python tiktok/matchsim/cli.py batch --fixtures tiktok/output/_fixtures.json --out-dir tiktok/output/_batch --pre 2 --live 8 --post 3
ls tiktok/output/_batch
```
Expect `mun-vs-liv.mp4` and `mun-vs-rma.mp4` plus their caption/post-notes. (gitignored.)

- [ ] **Step 7: Commit**
```bash
git add tiktok/matchsim/cli.py tiktok/matchsim/tests/test_batch.py
git commit -m "feat(matchsim): batch rendering + competition hashtags"
```

---

## Self-Review

**Spec coverage (M5–M7 polish + batch):**
- Win-prob % labels + swing callout → Tasks 1 + 4 ✓
- Title-safe header + symmetric scoreboard → Tasks 2 + 4 ✓
- Arena disc glow (possessing side) → Task 5 ✓
- Goal moment (flash + confetti + GOAL!) → Tasks 3 + 5 ✓
- Full-time fade-in → Task 5 ✓
- Caption glass pill → Task 4 ✓
- SFX (whoosh transitions + goal accents) → Task 6 ✓ (M7 audio)
- Batch mode with per-fixture isolation → Task 7 ✓ (M6)
- Competition hashtags → Task 7 ✓
- Explicitly deferred (documented, not gaps): slow-mo goal *replay* + ball tracer, animated ticker scroll, crest drop-in, momentum meter.

**Placeholder scan:** none — every code step is complete; visual tasks pair smoke tests with preview renders for sign-off.

**Type/name consistency:** `frame["swing"] = {"team","delta"}` (Task 1) is read in `_live_frame` (Task 4). `layout.live_zones()` gains `score_anchors` (Task 2), consumed in `_live_frame` (Task 4). `draw.halo(size,color,blur)` + `draw.confetti(w,h,seed,n)` (Task 3) are called in `_arena`/`_live_frame` (Task 5). `encode.encode(frames_dir,out_mp4,fps,sfx_events,duration)` (Task 6) is called from `_render_one` (Task 7) and the interim `_cmd_render` (Task 6). `_render_one(...)` (Task 7) centralizes the render pipeline used by both `render` and `batch`. All reuse the Plan 1–3 signatures (`engine.simulate`, `prepare.prepare`, `timeline.build_timeline`, `render_match.render_frames`) unchanged.

**Ordering note:** Task 5 Step 2 inserts the goal flash before `_live_frame`'s `return`; it depends on the Task 4 rewrite of `_live_frame` already being in place (Task 4 precedes Task 5). Task 7 depends on `encode.encode` accepting `sfx_events` (Task 6).
```
