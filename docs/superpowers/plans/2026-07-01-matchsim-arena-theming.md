# MatchSim Arena + Theming + Captions Implementation Plan (Plan 2 of 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure, fully-testable "render-ready data layer" for MatchSim — deterministic arena physics (clashing discs + ball), per-competition visual themes (with a United-red treatment), and an arcade-caption bank — then compose them with the engine's match-JSON into a single render-ready bundle exposed via a `prepare` CLI command.

**Architecture:** Three new pure modules in the existing flat `tiktok/matchsim/` dir. `arena.py` runs a deterministic 2-D physics sim (two team discs + a ball drifting and clashing inside a unit circle) and emits a normalized per-frame motion track + clash flags — it owns *visual motion*, never the match outcome (the engine owns that). `themes.py` resolves a competition key (+ whether Man Utd is involved) into a flat theme record the renderer reads instead of hard-coding colours. `captions.py` maps event flavours to arcade caption text, deterministically. `prepare.py` bundles `{match, theme, motion}` into one render-ready dict, surfaced by a `prepare` CLI subcommand. No pixels/video in this plan — that's Plan 3.

**Tech Stack:** Python 3, standard library only (`math`, `random`, `json`, `argparse`), `pytest`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-01-matchsim-design.md` (implements milestone M2). Plan 1 (the engine) is already merged/PR'd on this branch.

**Conventions (unchanged from Plan 1):**
- `tiktok/matchsim/` is a plain module dir (NO `__init__.py`); sibling modules import by bare name.
- Tests live in `tiktok/matchsim/tests/`; the existing `conftest.py` puts the `matchsim` dir on `sys.path`.
- Run all commands from repo root `C:\dev\Projects\The-Red-Mancunian`.
- Determinism: every random draw goes through a single seeded `random.Random(...)`. Same inputs + seed ⇒ identical output.

**The engine's match dict (already built, consumed here) looks like:**
```
{
  "fixture": {"home": {"name","abbr","color","monogram","crest"}, "away": {...},
              "competition": "ucl", "stage": "...", "venue": "...", "date": "...",
              "seed": 21, "final": "2-1"},
  "events": [{"minute","type","team"?,"flavour"?,"scorer"?,"scoreAfter"?}, ...],
  "winprob": [{"minute","home","draw","away"}, ...],
  "analytics": {"possession":[h,a], "shots":[h,a], "xg":[h,a]}
}
```
`event.type` ∈ {goal, near_miss, half_time, full_time}; `near_miss.flavour` ∈ {woodwork, big_chance, clash}.

---

### Task 1: Per-competition themes

**Files:**
- Create: `tiktok/matchsim/themes.py`
- Test: `tiktok/matchsim/tests/test_themes.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_themes.py`:

```python
from themes import resolve_theme, is_united, THEMES


def test_resolve_known_theme():
    t = resolve_theme("ucl")
    assert t["key"] == "ucl"
    assert t["name"] == "UEFA Champions League"
    assert t["bg"][0].startswith("#")
    assert t["united_home"] is False


def test_resolve_unknown_falls_back_to_generic():
    t = resolve_theme("nope")
    assert t["key"] == "generic"


def test_united_home_applies_red_accent():
    t = resolve_theme("ucl", united_home=True)
    assert t["united_home"] is True
    assert t["accent"] == "#DA020E"
    assert t["frame_glow"] == "#DA020E"


def test_non_united_frame_glow_is_theme_accent():
    t = resolve_theme("ucl", united_home=False)
    assert t["frame_glow"] == t["accent"]
    assert t["accent"] != "#DA020E"  # ucl base accent is cyan, not red


def test_resolve_does_not_mutate_module_theme():
    resolve_theme("ucl", united_home=True)
    assert THEMES["ucl"]["accent"] != "#DA020E"  # base dict untouched


def test_is_united_detects_either_side():
    def m(h, a):
        return {"fixture": {"home": {"abbr": h}, "away": {"abbr": a}}}
    assert is_united(m("MUN", "RMA")) is True
    assert is_united(m("RMA", "MUN")) is True
    assert is_united(m("LIV", "ARS")) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_themes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'themes'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/themes.py`:

```python
"""Per-competition visual themes. Pure data + a resolver.

The renderer reads ONLY the resolved theme (never hard-coded competition
colours), so adding a competition = adding a THEMES entry. When Man Utd are
involved, a red-accent "home" treatment is layered on top.
"""

RED_MANCUNIAN = "#DA020E"

# `bg` is a 3-stop vertical gradient; `trophy` is a glyph key the renderer maps
# to a drawn badge; `ticker` is the scrolling edge text.
THEMES = {
    "ucl": {
        "key": "ucl", "name": "UEFA Champions League",
        "bg": ["#0b1030", "#131a48", "#080b24"],
        "accent": "#39e6e6", "gold": "#F5C451",
        "text": "#dbe3ff", "muted": "#9fb0ff",
        "trophy": "star", "ticker": "UEFA CHAMPIONS LEAGUE",
    },
    "epl": {
        "key": "epl", "name": "Premier League",
        "bg": ["#1b0a2e", "#2d0b4e", "#12071f"],
        "accent": "#00ff87", "gold": "#F5C451",
        "text": "#efe6ff", "muted": "#b9a3d6",
        "trophy": "crown", "ticker": "PREMIER LEAGUE",
    },
    "wc": {
        "key": "wc", "name": "FIFA World Cup",
        "bg": ["#0a2a14", "#0f3d1d", "#071f0f"],
        "accent": "#35e0a0", "gold": "#F5C451",
        "text": "#e6fff0", "muted": "#9fd6b8",
        "trophy": "cup", "ticker": "FIFA WORLD CUP",
    },
    "generic": {
        "key": "generic", "name": "Football",
        "bg": ["#101018", "#1a1a2a", "#0a0a12"],
        "accent": "#39e6e6", "gold": "#F5C451",
        "text": "#e6e6f0", "muted": "#9f9fb0",
        "trophy": "ball", "ticker": "MATCH SIMULATION",
    },
}


def resolve_theme(competition_key, united_home=False):
    """Return a fresh theme dict (never mutate the module THEMES)."""
    base = THEMES.get((competition_key or "").lower(), THEMES["generic"])
    t = dict(base)
    t["bg"] = list(base["bg"])  # deep-copy the mutable list too
    t["united_home"] = bool(united_home)
    if united_home:
        t["accent"] = RED_MANCUNIAN
        t["frame_glow"] = RED_MANCUNIAN
    else:
        t["frame_glow"] = t["accent"]
    return t


def is_united(match):
    fx = match["fixture"]
    return fx["home"]["abbr"] == "MUN" or fx["away"]["abbr"] == "MUN"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_themes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/themes.py tiktok/matchsim/tests/test_themes.py
git commit -m "feat(matchsim): per-competition themes + United-red treatment"
```

---

### Task 2: Arcade caption bank

**Files:**
- Create: `tiktok/matchsim/captions.py`
- Test: `tiktok/matchsim/tests/test_captions.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_captions.py`:

```python
from captions import caption_for, POOLS


def test_goal_uses_goal_pool():
    ev = {"type": "goal", "team": "home", "scorer": "Kane"}
    assert caption_for(ev, seed=1, index=0) in POOLS["goal"]


def test_near_miss_uses_flavour_pool():
    ev = {"type": "near_miss", "flavour": "woodwork"}
    assert caption_for(ev, seed=1, index=0) in POOLS["woodwork"]


def test_unknown_flavour_falls_back_to_clash_pool():
    ev = {"type": "near_miss", "flavour": "totally_unknown"}
    assert caption_for(ev, seed=1, index=0) in POOLS["clash"]


def test_deterministic_for_same_seed_and_index():
    ev = {"type": "goal"}
    a = caption_for(ev, seed=7, index=3)
    b = caption_for(ev, seed=7, index=3)
    assert a == b


def test_index_varies_selection_within_pool():
    ev = {"type": "clash"} if False else {"type": "near_miss", "flavour": "clash"}
    picks = {caption_for(ev, seed=0, index=i) for i in range(len(POOLS["clash"]) * 2)}
    assert len(picks) > 1  # not stuck on a single caption


def test_captions_are_ascii_no_emoji():
    # Pillow's brand fonts can't render colour emoji, so captions stay ASCII.
    for pool in POOLS.values():
        for text in pool:
            assert text.isascii(), f"non-ascii caption: {text!r}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_captions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'captions'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/captions.py`:

```python
"""Arcade collision-caption bank, keyed to event type / near-miss flavour.

ASCII-only on purpose: the renderer draws captions with the Anton/Bebas brand
fonts, which have no colour-emoji glyphs. Selection is deterministic given
(seed, index) so a rendered match is reproducible.
"""

POOLS = {
    "goal": ["GOAL!!!", "SCREAMER!", "GET IN!", "SMASHED IT!"],
    "woodwork": ["OFF THE BAR!", "RATTLED THE POST!", "SO CLOSE!"],
    "big_chance": ["INCHES AWAY!", "NEARLY!", "WHAT A CHANCE!"],
    "clash": ["CLASH!", "SMASH CONTACT!", "CRUNCHING!"],
    "mystery_ball": ["MYSTERY BALL!", "CHAOS!"],
}

_FALLBACK = "clash"


def _pool_key(event):
    if event["type"] == "near_miss":
        return event.get("flavour", _FALLBACK)
    return event["type"]


def caption_for(event, seed, index):
    """Deterministically pick an arcade caption for an event."""
    key = _pool_key(event)
    pool = POOLS.get(key, POOLS[_FALLBACK])
    return pool[(seed + index) % len(pool)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_captions.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/captions.py tiktok/matchsim/tests/test_captions.py
git commit -m "feat(matchsim): arcade caption bank (deterministic, ascii)"
```

---

### Task 3: Deterministic arena physics

**Files:**
- Create: `tiktok/matchsim/arena.py`
- Test: `tiktok/matchsim/tests/test_arena.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_arena.py`:

```python
import math
from arena import simulate_motion, R, DISC_R


def _match(seed=21):
    return {"fixture": {"seed": seed}}


def test_frame_count_matches_request():
    frames = simulate_motion(_match(), n_frames=120)
    assert len(frames) == 120


def test_frame_shape():
    f = simulate_motion(_match(), n_frames=1)[0]
    assert set(f) == {"home", "away", "ball", "clash"}
    assert len(f["home"]) == 2 and len(f["ball"]) == 2
    assert isinstance(f["clash"], bool)


def test_discs_and_ball_stay_inside_arena():
    frames = simulate_motion(_match(), n_frames=400)
    for f in frames:
        assert math.hypot(*f["home"]) <= R + 1e-6
        assert math.hypot(*f["away"]) <= R + 1e-6
        assert math.hypot(*f["ball"]) <= R + 1e-6


def test_discs_never_overlap_after_a_frame_is_recorded():
    frames = simulate_motion(_match(), n_frames=400)
    for f in frames:
        dist = math.hypot(f["away"][0] - f["home"][0], f["away"][1] - f["home"][1])
        assert dist >= 2 * DISC_R - 1e-6


def test_deterministic_same_seed():
    a = simulate_motion(_match(21), n_frames=200)
    b = simulate_motion(_match(21), n_frames=200)
    assert a == b


def test_different_seed_diverges():
    a = simulate_motion(_match(1), n_frames=200)
    b = simulate_motion(_match(2), n_frames=200)
    assert a != b


def test_explicit_seed_overrides_fixture_seed():
    a = simulate_motion(_match(1), n_frames=50, seed=999)
    b = simulate_motion(_match(2), n_frames=50, seed=999)
    assert a == b


def test_some_clash_occurs_over_a_long_run():
    frames = simulate_motion(_match(), n_frames=1200)
    assert any(f["clash"] for f in frames)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_arena.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arena'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/arena.py`:

```python
"""Deterministic 2-D arena motion for the renderer.

Two team discs and a ball drift inside a unit circle (radius R), reflecting off
the wall and clashing off each other (equal-mass elastic). Output is a
normalized per-frame track (coords in the unit circle) plus a per-frame `clash`
flag that drives arcade captions. This owns VISUAL MOTION ONLY — the match
outcome is decided by the engine, never here.
"""
import math
import random

R = 1.0          # arena radius (normalized; renderer scales to pixels)
DISC_R = 0.20    # team-disc radius
BALL_R = 0.05    # ball radius
SPEED = 0.030    # base per-frame speed


def _reflect_inside(pos, vel, obj_r):
    """Keep an object inside the circle; reflect its velocity off the wall."""
    d = math.hypot(pos[0], pos[1])
    limit = R - obj_r
    if d > limit and d > 0:
        nx, ny = pos[0] / d, pos[1] / d
        pos[0], pos[1] = nx * limit, ny * limit
        dot = vel[0] * nx + vel[1] * ny
        vel[0] -= 2 * dot * nx
        vel[1] -= 2 * dot * ny


def _rand_pos(rng):
    ang = rng.uniform(0, 2 * math.pi)
    rad = rng.uniform(0.10, 0.50)
    return [math.cos(ang) * rad, math.sin(ang) * rad]


def _rand_vel(rng):
    ang = rng.uniform(0, 2 * math.pi)
    return [math.cos(ang) * SPEED, math.sin(ang) * SPEED]


def simulate_motion(match, n_frames, seed=None):
    s = match["fixture"]["seed"] if seed is None else seed
    rng = random.Random(s * 7919 + 13)  # decorrelate from the engine's rng

    home = {"pos": _rand_pos(rng), "vel": _rand_vel(rng)}
    away = {"pos": _rand_pos(rng), "vel": _rand_vel(rng)}
    ball = {"pos": [0.0, 0.0], "vel": _rand_vel(rng)}

    # Ensure discs don't start overlapping.
    while math.hypot(away["pos"][0] - home["pos"][0],
                     away["pos"][1] - home["pos"][1]) < 2 * DISC_R:
        away["pos"] = _rand_pos(rng)

    frames = []
    for _ in range(n_frames):
        for obj, r in ((home, DISC_R), (away, DISC_R), (ball, BALL_R)):
            obj["pos"][0] += obj["vel"][0]
            obj["pos"][1] += obj["vel"][1]
            _reflect_inside(obj["pos"], obj["vel"], r)

        clash = False
        dx = away["pos"][0] - home["pos"][0]
        dy = away["pos"][1] - home["pos"][1]
        dist = math.hypot(dx, dy)
        if 0 < dist < 2 * DISC_R:
            clash = True
            nx, ny = dx / dist, dy / dist
            overlap = 2 * DISC_R - dist
            home["pos"][0] -= nx * overlap / 2
            home["pos"][1] -= ny * overlap / 2
            away["pos"][0] += nx * overlap / 2
            away["pos"][1] += ny * overlap / 2
            hv = home["vel"][0] * nx + home["vel"][1] * ny
            av = away["vel"][0] * nx + away["vel"][1] * ny
            home["vel"][0] += (av - hv) * nx
            home["vel"][1] += (av - hv) * ny
            away["vel"][0] += (hv - av) * nx
            away["vel"][1] += (hv - av) * ny

        frames.append({
            "home": [round(home["pos"][0], 4), round(home["pos"][1], 4)],
            "away": [round(away["pos"][0], 4), round(away["pos"][1], 4)],
            "ball": [round(ball["pos"][0], 4), round(ball["pos"][1], 4)],
            "clash": clash,
        })
    return frames
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_arena.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/arena.py tiktok/matchsim/tests/test_arena.py
git commit -m "feat(matchsim): deterministic arena physics (discs + ball + clash)"
```

---

### Task 4: Render-ready bundle (`prepare`)

**Files:**
- Create: `tiktok/matchsim/prepare.py`
- Test: `tiktok/matchsim/tests/test_prepare.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_prepare.py`:

```python
from engine import simulate
from prepare import prepare


def test_bundle_shape():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    b = prepare(m, n_frames=100)
    assert set(b) == {"match", "theme", "motion"}
    assert b["match"] is m
    assert b["theme"]["key"] == "ucl"
    assert len(b["motion"]) == 100


def test_united_match_gets_red_treatment():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    b = prepare(m, n_frames=10)
    assert b["theme"]["united_home"] is True
    assert b["theme"]["accent"] == "#DA020E"


def test_non_united_match_keeps_theme_accent():
    m = simulate("LIV", "ARS", competition="epl", seed=5)
    b = prepare(m, n_frames=10)
    assert b["theme"]["united_home"] is False
    assert b["theme"]["accent"] != "#DA020E"


def test_motion_seeded_from_match():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    a = prepare(m, n_frames=50)["motion"]
    b = prepare(m, n_frames=50)["motion"]
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_prepare.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'prepare'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/prepare.py`:

```python
"""Compose the engine's match dict with a resolved theme and an arena motion
track into a single render-ready bundle. This is the artifact the Plan 3
renderer consumes; it has no pixel/video concerns.
"""
import arena
import themes


def prepare(match, n_frames):
    theme = themes.resolve_theme(
        match["fixture"]["competition"],
        united_home=themes.is_united(match),
    )
    motion = arena.simulate_motion(match, n_frames=n_frames)
    return {"match": match, "theme": theme, "motion": motion}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_prepare.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/prepare.py tiktok/matchsim/tests/test_prepare.py
git commit -m "feat(matchsim): render-ready bundle (match + theme + motion)"
```

---

### Task 5: `prepare` CLI subcommand

**Files:**
- Modify: `tiktok/matchsim/cli.py`
- Test: `tiktok/matchsim/tests/test_cli_prepare.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_cli_prepare.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")


def test_cli_prepare_writes_bundle(tmp_path):
    out = tmp_path / "bundle.json"
    r = subprocess.run(
        [sys.executable, CLI, "prepare", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21", "--frames", "60",
         "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert set(data) == {"match", "theme", "motion"}
    assert data["theme"]["key"] == "ucl"
    assert data["theme"]["united_home"] is True
    assert len(data["motion"]) == 60
    assert data["match"]["events"][-1]["type"] == "full_time"


def test_cli_simulate_still_works(tmp_path):
    # Regression: the existing simulate subcommand must be unaffected.
    r = subprocess.run(
        [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
         "--seed", "21"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["fixture"]["home"]["abbr"] == "MUN"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_cli_prepare.py -v`
Expected: FAIL — the `prepare` subcommand does not exist (argparse errors / non-zero exit).

- [ ] **Step 3: Add the subcommand.** In `tiktok/matchsim/cli.py`, add `import prepare as prepare_mod` next to the existing `import engine` / `import schema` lines. Add this handler function next to `_cmd_simulate`:

```python
def _cmd_prepare(args):
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
    bundle = prepare_mod.prepare(m, n_frames=args.frames)
    public = {"match": {k: v for k, v in bundle["match"].items()
                        if not k.startswith("_")},
              "theme": bundle["theme"], "motion": bundle["motion"]}
    text = json.dumps(public, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0
```

Then, in `main`, after the existing `simulate` subparser block (the line `s.set_defaults(func=_cmd_simulate)`), register a `prepare` subparser that shares the same team/xg options plus `--frames`:

```python
    p = sub.add_parser("prepare", help="simulate + theme + motion -> render-ready bundle JSON")
    p.add_argument("--home", required=True)
    p.add_argument("--away", required=True)
    p.add_argument("--competition", default="generic")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    p.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    p.add_argument("--venue", default="")
    p.add_argument("--stage", default=None)
    p.add_argument("--date", default="")
    p.add_argument("--frames", type=int, default=1140,
                   help="arena motion frames (default 1140 = ~38s at 30fps)")
    p.add_argument("--out", default=None)
    p.set_defaults(func=_cmd_prepare)
```

- [ ] **Step 4: Run the new test AND the existing CLI test**

Run: `python -m pytest tiktok/matchsim/tests/test_cli_prepare.py tiktok/matchsim/tests/test_cli.py -v`
Expected: PASS (2 + 2 = 4 passed)

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest tiktok/matchsim/tests/ -v`
Expected: PASS (all Plan 1 + Plan 2 tests green)

- [ ] **Step 6: Manual smoke check**

Run: `python tiktok/matchsim/cli.py prepare --home MUN --away RMA --competition ucl --seed 21 --frames 60 --out tiktok/output/_tmp/bundle.json`
Expected: prints `wrote ...`; the file has `match`/`theme`/`motion`, `theme.united_home` true, `theme.accent` `#DA020E`, 60 motion frames. (The `tiktok/output/` dir is gitignored — safe to leave.)

- [ ] **Step 7: Commit**

```bash
git add tiktok/matchsim/cli.py tiktok/matchsim/tests/test_cli_prepare.py
git commit -m "feat(matchsim): prepare CLI -> render-ready bundle"
```

---

## Self-Review

**Spec coverage (M2 scope):**
- Arena-clash physics (discs + ball + clash events) → Task 3 ✓
- Per-competition theme system + United-red treatment (spec §5) → Task 1 ✓
- Arcade collision captions keyed to flavours (spec §7, Act 2) → Task 2 ✓
- Render-ready composition (the artifact the Plan 3 renderer consumes) → Tasks 4–5 ✓
- Out of Plan-2 scope (documented as later plans): `render_match.py` Pillow renderer, three-act frames, goal replay/tracer/confetti, SFX mux, batch mode, `matchsim.py` orchestration → Plans 3–4.

**Placeholder scan:** none — every step has full code and exact commands.

**Type/name consistency:** `resolve_theme(competition_key, united_home)` and `is_united(match)` (themes) are used exactly that way in `prepare.py` and the CLI. `caption_for(event, seed, index)` + `POOLS` (captions) match their tests. `simulate_motion(match, n_frames, seed=None)` + module constants `R`, `DISC_R`, `BALL_R` are consistent across `arena.py`, its tests, and `prepare.py`. `prepare(match, n_frames)` returns `{"match","theme","motion"}` — the same keys asserted in Tasks 4 and 5. The CLI reuses the Plan 1 `engine.simulate(...)` signature and the `_`-key stripping + `SchemaError` handling patterns already established in `_cmd_simulate`.

**Consistency with engine output (verified against live CLI):** `fixture.competition`, `fixture.seed`, `fixture.home.abbr`, and `near_miss.flavour` ∈ {woodwork, big_chance, clash} all match what `engine.simulate` actually emits, so `is_united`, `simulate_motion` seeding, and `caption_for` key off real fields.

**Note on captions & emoji:** the spec mockups showed emoji in arcade pills; captions here are intentionally ASCII because the Pillow brand fonts (Anton/Bebas) can't render colour-emoji glyphs. The renderer (Plan 3) can draw a small vector icon beside a caption if an emoji-like flourish is wanted — tracked as a Plan 3 concern, not a gap here.
```
