# MatchSim Engine Core Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the pure statistical match engine that turns two teams + a competition + a seed into an inspectable match-JSON (final score, minute-stamped events, a live Dixon-Coles win-probability track, and full-time analytics), exposed via a `simulate` CLI.

**Architecture:** A flat module directory `tiktok/matchsim/` (mirroring the repo's existing flat-module convention in `tiktok/`). A vendored Dixon-Coles core produces a score-probability matrix; the engine samples a scoreline from it with a seeded RNG, places goal/near-miss events across 90 minutes, recomputes win-probability over the remaining match at checkpoints, and derives credible analytics. The match dict is the language-agnostic contract consumed later by the renderer. No video concerns in this plan.

**Tech Stack:** Python 3, standard library only (`math`, `random`, `json`, `argparse`), `pytest` for tests. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-01-matchsim-design.md` (this plan implements milestone M1).

**Conventions:**
- `tiktok/matchsim/` is a plain module directory (NOT a package — no `__init__.py`), like `tiktok/` itself where `render.py` does `import frames`. Sibling modules import by bare name (`from dixon_coles import score_matrix`).
- Tests live in `tiktok/matchsim/tests/`. A `conftest.py` puts the `matchsim` dir on `sys.path` so bare imports resolve.
- Run all commands from the repo root `C:\dev\Projects\The-Red-Mancunian`.
- Determinism: the engine uses a single `random.Random(seed)` instance threaded through all sampling. Same inputs + seed ⇒ identical JSON.

---

### Task 1: Test harness + vendored Dixon-Coles core

**Files:**
- Create: `tiktok/matchsim/tests/conftest.py`
- Create: `tiktok/matchsim/dixon_coles.py`
- Test: `tiktok/matchsim/tests/test_dixon_coles.py`

- [ ] **Step 1: Create the test path bootstrap**

Create `tiktok/matchsim/tests/conftest.py`:

```python
"""Put the matchsim module dir on sys.path so tests can `import dixon_coles` etc."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
```

- [ ] **Step 2: Write the failing test**

Create `tiktok/matchsim/tests/test_dixon_coles.py`:

```python
from dixon_coles import poisson_pmf, score_matrix, derive_markets


def test_poisson_pmf_zero_lambda():
    assert poisson_pmf(0, 0.0) == 1.0
    assert poisson_pmf(1, 0.0) == 0.0


def test_score_matrix_sums_to_one():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    total = sum(m[i][j] for i in range(11) for j in range(11))
    assert abs(total - 1.0) < 1e-9


def test_derive_markets_probabilities_consistent():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    mk = derive_markets(m, 10)
    o = mk["1x2"]
    assert abs(o["home"] + o["draw"] + o["away"] - 1.0) < 1e-9
    # stronger home xG should make home the most likely single outcome
    assert o["home"] > o["away"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_dixon_coles.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dixon_coles'`

- [ ] **Step 4: Write the implementation (vendored from match_model.py)**

Create `tiktok/matchsim/dixon_coles.py`:

```python
"""Vendored Dixon-Coles bivariate-Poisson core.

Refactored out of the match-analyst skill's match_model.py so MatchSim is
self-contained (the skill's copy lives in a transient extracted dir).
Produces P(home i, away j) as a normalized score matrix.
"""
from math import exp, factorial


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * exp(-lam) / factorial(k)


def dc_tau(i, j, lam, mu, rho):
    """Dixon-Coles low-score dependency adjustment."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(home_xg, away_xg, rho=-0.05, max_goals=10):
    """Return matrix[i][j] = P(home scores i, away scores j), normalized."""
    m = [[0.0] * (max_goals + 1) for _ in range(max_goals + 1)]
    total = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = (poisson_pmf(i, home_xg)
                 * poisson_pmf(j, away_xg)
                 * dc_tau(i, j, home_xg, away_xg, rho))
            p = max(p, 0.0)  # tau can go slightly negative for extreme rho
            m[i][j] = p
            total += p
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i][j] /= total
    return m


def derive_markets(m, max_goals):
    home = draw = away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = m[i][j]
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    return {"1x2": {"home": home, "draw": draw, "away": away}}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_dixon_coles.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add tiktok/matchsim/dixon_coles.py tiktok/matchsim/tests/conftest.py tiktok/matchsim/tests/test_dixon_coles.py
git commit -m "feat(matchsim): vendored Dixon-Coles core + test harness"
```

---

### Task 2: Live win-probability

**Files:**
- Create: `tiktok/matchsim/winprob.py`
- Test: `tiktok/matchsim/tests/test_winprob.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_winprob.py`:

```python
from winprob import win_prob


def test_sums_to_one_at_kickoff():
    wp = win_prob(0, 0, minutes_left=90, lam_h=1.6, lam_a=1.1)
    assert abs(wp["home"] + wp["draw"] + wp["away"] - 1.0) < 1e-9


def test_full_time_decided_by_current_score():
    wp = win_prob(2, 1, minutes_left=0, lam_h=1.6, lam_a=1.1)
    assert wp["home"] == 1.0
    assert wp["draw"] == 0.0
    assert wp["away"] == 0.0


def test_full_time_draw():
    wp = win_prob(1, 1, minutes_left=0, lam_h=1.6, lam_a=1.1)
    assert wp["draw"] == 1.0


def test_a_home_goal_raises_home_probability():
    before = win_prob(0, 0, minutes_left=60, lam_h=1.4, lam_a=1.4)
    after = win_prob(1, 0, minutes_left=60, lam_h=1.4, lam_a=1.4)
    assert after["home"] > before["home"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_winprob.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'winprob'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/winprob.py`:

```python
"""Live win probability: Dixon-Coles over the REMAINING match, folded onto
the current score. At minutes_left=0 the outcome is fully decided by the
current score.
"""
from dixon_coles import score_matrix


def win_prob(score_h, score_a, minutes_left, lam_h, lam_a, rho=-0.05, max_goals=8):
    frac = max(0.0, minutes_left / 90.0)
    m = score_matrix(lam_h * frac, lam_a * frac, rho, max_goals)
    home = draw = away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            fh, fa = score_h + i, score_a + j
            p = m[i][j]
            if fh > fa:
                home += p
            elif fh == fa:
                draw += p
            else:
                away += p
    return {"home": home, "draw": draw, "away": away}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_winprob.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/winprob.py tiktok/matchsim/tests/test_winprob.py
git commit -m "feat(matchsim): live Dixon-Coles win-probability"
```

---

### Task 3: Team & competition presets + xG derivation

**Files:**
- Create: `tiktok/matchsim/presets.py`
- Test: `tiktok/matchsim/tests/test_presets.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_presets.py`:

```python
import pytest
from presets import resolve_team, resolve_competition, compute_xg


def test_resolve_known_team_by_abbr():
    t = resolve_team("MUN")
    assert t["name"] == "Man Utd"
    assert t["abbr"] == "MUN"
    assert t["color"].startswith("#")
    assert isinstance(t["scorers"], list) and t["scorers"]
    assert t["crest"] is None


def test_resolve_unknown_team_from_dict():
    t = resolve_team({"name": "Wrexham", "abbr": "WRX", "color": "#FF0000"})
    assert t["name"] == "Wrexham"
    assert t["monogram"] == "WRX"       # falls back to abbr
    assert t["attack"] > 0 and t["defense"] > 0  # defaulted
    assert t["scorers"]                  # generic pool


def test_resolve_unknown_team_missing_fields_raises():
    with pytest.raises(ValueError):
        resolve_team({"name": "NoAbbr"})


def test_resolve_competition():
    c = resolve_competition("ucl")
    assert c["key"] == "ucl"
    assert "name" in c and "default_stage" in c


def test_resolve_competition_unknown_falls_back_to_generic():
    c = resolve_competition("nope")
    assert c["key"] == "generic"


def test_compute_xg_home_advantage():
    home = resolve_team("MUN")
    away = resolve_team("MUN")
    lam_h, lam_a = compute_xg(home, away)
    assert lam_h > lam_a  # identical teams: home advantage tips it
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_presets.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'presets'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/presets.py`:

```python
"""Team + competition presets, and xG derivation from strength ratings.

`attack` ~ goals a side tends to score vs average; `defense` ~ goals it tends
to concede (1.0 = average, <1.0 = solid, >1.0 = leaky). xG derivation applies
a home-advantage multiplier.
"""

HOME_ADV = 1.15

GENERIC_SCORERS = ["No. 9", "No. 10", "No. 7", "No. 11", "No. 8"]

TEAMS = {
    "MUN": {"name": "Man Utd", "color": "#DA020E", "monogram": "MUN",
            "attack": 1.75, "defense": 0.95,
            "scorers": ["Hojlund", "Garnacho", "Fernandes", "Mount", "Zirkzee"]},
    "MCI": {"name": "Man City", "color": "#6CABDD", "monogram": "MCI",
            "attack": 2.05, "defense": 0.80,
            "scorers": ["Haaland", "Foden", "Doku", "Alvarez"]},
    "LIV": {"name": "Liverpool", "color": "#C8102E", "monogram": "LIV",
            "attack": 1.95, "defense": 0.85,
            "scorers": ["Salah", "Nunez", "Diaz", "Gakpo"]},
    "ARS": {"name": "Arsenal", "color": "#EF0107", "monogram": "ARS",
            "attack": 1.90, "defense": 0.82,
            "scorers": ["Saka", "Jesus", "Odegaard", "Havertz"]},
    "RMA": {"name": "Real Madrid", "color": "#FEBE10", "monogram": "RMA",
            "attack": 2.00, "defense": 0.85,
            "scorers": ["Mbappe", "Vinicius", "Bellingham", "Rodrygo"]},
    "BAR": {"name": "Barcelona", "color": "#A50044", "monogram": "BAR",
            "attack": 1.95, "defense": 0.90,
            "scorers": ["Lewandowski", "Yamal", "Raphinha", "Pedri"]},
    "BAY": {"name": "Bayern", "color": "#DC052D", "monogram": "BAY",
            "attack": 2.00, "defense": 0.88,
            "scorers": ["Kane", "Musiala", "Sane", "Olise"]},
    "ENG": {"name": "England", "color": "#FFFFFF", "monogram": "ENG",
            "attack": 1.80, "defense": 0.85,
            "scorers": ["Kane", "Bellingham", "Foden", "Saka"]},
    "FRA": {"name": "France", "color": "#0055A4", "monogram": "FRA",
            "attack": 1.90, "defense": 0.85,
            "scorers": ["Mbappe", "Griezmann", "Dembele", "Kolo Muani"]},
}

COMPETITIONS = {
    "ucl": {"key": "ucl", "name": "UEFA Champions League",
            "default_stage": "League Phase"},
    "epl": {"key": "epl", "name": "Premier League",
            "default_stage": "Matchweek 1"},
    "wc": {"key": "wc", "name": "FIFA World Cup",
           "default_stage": "Group Stage"},
    "generic": {"key": "generic", "name": "Football",
                "default_stage": "Friendly"},
}


def resolve_team(x):
    """Accept an abbr key (str) or a dict of overrides. Returns a full record."""
    if isinstance(x, str):
        key = x.upper()
        if key not in TEAMS:
            raise ValueError(f"unknown team abbr {x!r}; pass a dict to override")
        base = {"abbr": key, **TEAMS[key]}
    elif isinstance(x, dict):
        if not x.get("name") or not x.get("abbr") or not x.get("color"):
            raise ValueError("team dict needs at least name, abbr, color")
        base = dict(x)
    else:
        raise ValueError(f"team must be str or dict, got {type(x)}")
    base.setdefault("monogram", base["abbr"][:3].upper())
    base.setdefault("attack", 1.3)
    base.setdefault("defense", 1.0)
    base.setdefault("scorers", list(GENERIC_SCORERS))
    base.setdefault("crest", None)
    return base


def resolve_competition(key):
    return COMPETITIONS.get((key or "").lower(), COMPETITIONS["generic"])


def compute_xg(home, away):
    lam_h = home["attack"] * away["defense"] * HOME_ADV
    lam_a = away["attack"] * home["defense"]
    return lam_h, lam_a
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_presets.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/presets.py tiktok/matchsim/tests/test_presets.py
git commit -m "feat(matchsim): team + competition presets and xG derivation"
```

---

### Task 4: Score sampling + simulate() skeleton

**Files:**
- Create: `tiktok/matchsim/engine.py`
- Test: `tiktok/matchsim/tests/test_engine_score.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_engine_score.py`:

```python
from engine import simulate


def test_deterministic_same_seed():
    a = simulate("MUN", "RMA", competition="ucl", seed=42)
    b = simulate("MUN", "RMA", competition="ucl", seed=42)
    assert a == b


def test_different_seed_can_differ():
    a = simulate("MUN", "RMA", competition="ucl", seed=1)
    b = simulate("MUN", "RMA", competition="ucl", seed=2)
    # not guaranteed different, but fixture block should carry the seed
    assert a["fixture"]["seed"] == 1
    assert b["fixture"]["seed"] == 2


def test_fixture_block_shape():
    m = simulate("MUN", "RMA", competition="ucl", seed=7, venue="Old Trafford")
    fx = m["fixture"]
    assert fx["home"]["abbr"] == "MUN"
    assert fx["away"]["abbr"] == "RMA"
    assert fx["competition"] == "ucl"
    assert fx["venue"] == "Old Trafford"
    assert fx["final"] == m["_final"]  # final string matches sampled score


def test_xg_override_used():
    m = simulate("MUN", "RMA", seed=3, home_xg=3.0, away_xg=0.1)
    # with a huge home xG and tiny away xG, home should very likely win
    sh, sa = (int(x) for x in m["_final"].split("-"))
    assert sh >= sa
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'engine'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/engine.py`:

```python
"""Pure statistical match engine: fixture -> match dict.

Samples a scoreline from the Dixon-Coles matrix, then (in later tasks) builds
events, a win-prob track, and analytics. Deterministic per seed.
"""
import random

import presets
from dixon_coles import score_matrix

RHO = -0.05
MAX_GOALS = 8


def _sample_score(lam_h, lam_a, rng):
    m = score_matrix(lam_h, lam_a, RHO, MAX_GOALS)
    r = rng.random()
    cum = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            cum += m[i][j]
            if r <= cum:
                return i, j
    return MAX_GOALS, MAX_GOALS


def _disc(team):
    return {
        "name": team["name"], "abbr": team["abbr"], "color": team["color"],
        "monogram": team["monogram"], "crest": team.get("crest"),
    }


def simulate(home, away, competition="generic", seed=0,
             home_xg=None, away_xg=None, venue="", stage=None, date=""):
    rng = random.Random(seed)
    h = presets.resolve_team(home)
    a = presets.resolve_team(away)
    comp = presets.resolve_competition(competition)

    if home_xg is None or away_xg is None:
        lam_h, lam_a = presets.compute_xg(h, a)
    else:
        lam_h, lam_a = home_xg, away_xg

    sh, sa = _sample_score(lam_h, lam_a, rng)
    final = f"{sh}-{sa}"

    return {
        "fixture": {
            "home": _disc(h), "away": _disc(a),
            "competition": comp["key"],
            "stage": stage if stage is not None else comp["default_stage"],
            "venue": venue, "date": date, "seed": seed, "final": final,
        },
        "_final": final,      # internal convenience; mirrors fixture.final
        "_lam": [lam_h, lam_a],
        "_score": [sh, sa],
        "_rng_state": None,   # placeholder; events task threads `rng` directly
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_score.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/engine.py tiktok/matchsim/tests/test_engine_score.py
git commit -m "feat(matchsim): deterministic score sampling + simulate skeleton"
```

---

### Task 5: Event timeline (goals, near-misses, half/full-time)

**Files:**
- Modify: `tiktok/matchsim/engine.py`
- Test: `tiktok/matchsim/tests/test_engine_events.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_engine_events.py`:

```python
from engine import simulate


def _events(m):
    return m["events"]


def test_goal_count_matches_final_score():
    m = simulate("MUN", "RMA", seed=11)
    sh, sa = (int(x) for x in m["fixture"]["final"].split("-"))
    goals = [e for e in _events(m) if e["type"] == "goal"]
    assert len([g for g in goals if g["team"] == "home"]) == sh
    assert len([g for g in goals if g["team"] == "away"]) == sa


def test_has_half_time_and_full_time():
    ev = _events(simulate("MUN", "RMA", seed=11))
    types = [e["type"] for e in ev]
    assert types.count("half_time") == 1
    assert types.count("full_time") == 1
    assert ev[-1]["type"] == "full_time"


def test_events_sorted_by_minute():
    ev = _events(simulate("MUN", "RMA", seed=11))
    minutes = [e["minute"] for e in ev]
    assert minutes == sorted(minutes)


def test_full_time_scoreafter_matches_final():
    m = simulate("MUN", "RMA", seed=11)
    ft = [e for e in _events(m) if e["type"] == "full_time"][0]
    assert ft["scoreAfter"] == m["fixture"]["final"]


def test_goals_have_scorer_from_pool():
    m = simulate("MUN", "RMA", seed=5, home_xg=3.0, away_xg=0.05)
    from presets import resolve_team
    pool = set(resolve_team("MUN")["scorers"])
    home_goals = [e for e in _events(m) if e["type"] == "goal" and e["team"] == "home"]
    assert home_goals  # near-certain with xG 3.0
    assert all(g["scorer"] in pool for g in home_goals)


def test_near_miss_events_present_with_flavour():
    ev = _events(simulate("MUN", "RMA", seed=11))
    nm = [e for e in ev if e["type"] == "near_miss"]
    assert nm
    assert all(e["flavour"] in {"woodwork", "big_chance", "clash"} for e in nm)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_events.py -v`
Expected: FAIL — `KeyError: 'events'`

- [ ] **Step 3: Add the event builder and wire it into simulate()**

In `tiktok/matchsim/engine.py`, add this function above `simulate`:

```python
_EVENT_ORDER = {"goal": 0, "near_miss": 1, "half_time": 2, "full_time": 3}


def _build_events(sh, sa, h, a, rng):
    raw = []
    for _ in range(sh):
        raw.append({"minute": rng.randint(1, 90), "type": "goal", "team": "home"})
    for _ in range(sa):
        raw.append({"minute": rng.randint(1, 90), "type": "goal", "team": "away"})
    for _ in range(rng.randint(2, 4)):
        raw.append({
            "minute": rng.randint(1, 90), "type": "near_miss",
            "team": "home" if rng.random() < 0.5 else "away",
            "flavour": rng.choice(["woodwork", "big_chance", "clash"]),
        })
    raw.append({"minute": 45, "type": "half_time"})
    raw.append({"minute": 90, "type": "full_time"})
    raw.sort(key=lambda e: (e["minute"], _EVENT_ORDER[e["type"]]))

    ch = ca = 0
    for e in raw:
        if e["type"] == "goal":
            if e["team"] == "home":
                ch += 1
            else:
                ca += 1
            team = h if e["team"] == "home" else a
            e["scorer"] = rng.choice(team["scorers"])
            e["scoreAfter"] = f"{ch}-{ca}"
        elif e["type"] in ("half_time", "full_time"):
            e["scoreAfter"] = f"{ch}-{ca}"
    return raw
```

Then in `simulate`, replace the `return {...}` block so it computes and includes events. The full updated tail of `simulate` becomes:

```python
    sh, sa = _sample_score(lam_h, lam_a, rng)
    final = f"{sh}-{sa}"
    events = _build_events(sh, sa, h, a, rng)

    return {
        "fixture": {
            "home": _disc(h), "away": _disc(a),
            "competition": comp["key"],
            "stage": stage if stage is not None else comp["default_stage"],
            "venue": venue, "date": date, "seed": seed, "final": final,
        },
        "events": events,
        "_final": final,
        "_lam": [lam_h, lam_a],
        "_score": [sh, sa],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_events.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Re-run the score test to confirm no regression**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_score.py -v`
Expected: PASS (4 passed) — note `test_fixture_block_shape` still passes because `_final` is still present.

- [ ] **Step 6: Commit**

```bash
git add tiktok/matchsim/engine.py tiktok/matchsim/tests/test_engine_events.py
git commit -m "feat(matchsim): minute-stamped event timeline"
```

---

### Task 6: Win-prob track + analytics

**Files:**
- Modify: `tiktok/matchsim/engine.py`
- Test: `tiktok/matchsim/tests/test_engine_winprob_analytics.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_engine_winprob_analytics.py`:

```python
from engine import simulate


def test_winprob_track_present_and_normalized():
    m = simulate("MUN", "RMA", seed=9)
    track = m["winprob"]
    assert track and track[0]["minute"] == 0
    assert track[-1]["minute"] == 90
    for pt in track:
        assert abs(pt["home"] + pt["draw"] + pt["away"] - 1.0) < 0.02


def test_winprob_track_includes_every_goal_minute():
    m = simulate("MUN", "RMA", seed=9)
    goal_minutes = {e["minute"] for e in m["events"] if e["type"] == "goal"}
    track_minutes = {pt["minute"] for pt in m["winprob"]}
    assert goal_minutes <= track_minutes


def test_analytics_shape():
    m = simulate("MUN", "RMA", seed=9)
    an = m["analytics"]
    assert an["possession"][0] + an["possession"][1] == 100
    sh, sa = m["_score"]
    assert an["shots"][0] >= sh and an["shots"][1] >= sa
    assert an["xg"][0] > 0 and an["xg"][1] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_winprob_analytics.py -v`
Expected: FAIL — `KeyError: 'winprob'`

- [ ] **Step 3: Add the builders and wire them into simulate()**

In `tiktok/matchsim/engine.py`, add the import at the top (next to the other imports):

```python
from winprob import win_prob
```

Add these two functions above `simulate`:

```python
def _winprob_track(events, lam_h, lam_a):
    goal_minutes = [e["minute"] for e in events if e["type"] == "goal"]
    checkpoints = sorted(set([0, 15, 30, 45, 60, 75, 90] + goal_minutes))
    track = []
    for minute in checkpoints:
        ch = ca = 0
        for e in events:
            if e["type"] == "goal" and e["minute"] <= minute:
                if e["team"] == "home":
                    ch += 1
                else:
                    ca += 1
        wp = win_prob(ch, ca, 90 - minute, lam_h, lam_a)
        track.append({
            "minute": minute,
            "home": round(wp["home"], 3),
            "draw": round(wp["draw"], 3),
            "away": round(wp["away"], 3),
        })
    return track


def _analytics(sh, sa, lam_h, lam_a, rng):
    tot = max(lam_h + lam_a, 0.1)
    poss_h = 50 + (lam_h - lam_a) / tot * 20 + rng.uniform(-4, 4)
    poss_h = int(max(35, min(65, round(poss_h))))
    shots_h = max(sh, int(round(lam_h * 6 + rng.uniform(-2, 2))))
    shots_a = max(sa, int(round(lam_a * 6 + rng.uniform(-2, 2))))
    xg_h = round(max(0.1, lam_h + rng.uniform(-0.2, 0.2)), 1)
    xg_a = round(max(0.1, lam_a + rng.uniform(-0.2, 0.2)), 1)
    return {
        "possession": [poss_h, 100 - poss_h],
        "shots": [shots_h, shots_a],
        "xg": [xg_h, xg_a],
    }
```

Then update the `return` block in `simulate` to add the two keys (place after `events` is built):

```python
    events = _build_events(sh, sa, h, a, rng)
    winprob = _winprob_track(events, lam_h, lam_a)
    analytics = _analytics(sh, sa, lam_h, lam_a, rng)

    return {
        "fixture": {
            "home": _disc(h), "away": _disc(a),
            "competition": comp["key"],
            "stage": stage if stage is not None else comp["default_stage"],
            "venue": venue, "date": date, "seed": seed, "final": final,
        },
        "events": events,
        "winprob": winprob,
        "analytics": analytics,
        "_final": final,
        "_lam": [lam_h, lam_a],
        "_score": [sh, sa],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_engine_winprob_analytics.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/engine.py tiktok/matchsim/tests/test_engine_winprob_analytics.py
git commit -m "feat(matchsim): win-prob track + credible analytics"
```

---

### Task 7: Match-JSON schema validation

**Files:**
- Create: `tiktok/matchsim/schema.py`
- Test: `tiktok/matchsim/tests/test_schema.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_schema.py`:

```python
import pytest
from engine import simulate
from schema import validate, SchemaError


def test_simulate_output_validates():
    m = simulate("MUN", "RMA", competition="ucl", seed=13)
    assert validate(m) is m


def test_missing_key_raises():
    m = simulate("MUN", "RMA", seed=13)
    del m["winprob"]
    with pytest.raises(SchemaError):
        validate(m)


def test_bad_event_type_raises():
    m = simulate("MUN", "RMA", seed=13)
    m["events"][0]["type"] = "bogus"
    with pytest.raises(SchemaError):
        validate(m)


def test_bad_scoreafter_format_raises():
    m = simulate("MUN", "RMA", seed=13)
    ft = [e for e in m["events"] if e["type"] == "full_time"][0]
    ft["scoreAfter"] = "2:1"
    with pytest.raises(SchemaError):
        validate(m)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'schema'`

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/schema.py`:

```python
"""Validation for the match dict — mirrors tiktok/story.py's validate() style so
engine bugs are caught without rendering (spec NFR4)."""
import re

EVENT_TYPES = {"goal", "near_miss", "clash", "mystery_ball", "half_time", "full_time"}
_SCORE_RE = re.compile(r"^\d+-\d+$")


class SchemaError(ValueError):
    pass


def _require(cond, msg):
    if not cond:
        raise SchemaError(msg)


def validate(m):
    for key in ("fixture", "events", "winprob", "analytics"):
        _require(key in m, f"missing required key: {key!r}")

    fx = m["fixture"]
    for key in ("home", "away", "competition", "seed", "final"):
        _require(key in fx, f"fixture missing {key!r}")
    _require(_SCORE_RE.match(fx["final"]), f"fixture.final must be 'H-A', got {fx['final']!r}")
    for side in ("home", "away"):
        for key in ("name", "abbr", "color", "monogram"):
            _require(key in fx[side], f"fixture.{side} missing {key!r}")

    _require(isinstance(m["events"], list) and m["events"], "events must be a non-empty list")
    for i, e in enumerate(m["events"]):
        _require(e.get("type") in EVENT_TYPES, f"events[{i}] bad type {e.get('type')!r}")
        _require(isinstance(e.get("minute"), int) and 0 <= e["minute"] <= 120,
                 f"events[{i}] bad minute {e.get('minute')!r}")
        if e["type"] in ("goal", "half_time", "full_time"):
            _require(_SCORE_RE.match(e.get("scoreAfter", "")),
                     f"events[{i}] bad scoreAfter {e.get('scoreAfter')!r}")
        if e["type"] == "goal":
            _require(e.get("team") in ("home", "away"), f"events[{i}] bad team")
            _require(bool(e.get("scorer")), f"events[{i}] goal missing scorer")
    _require(m["events"][-1]["type"] == "full_time", "last event must be full_time")

    for i, pt in enumerate(m["winprob"]):
        s = pt["home"] + pt["draw"] + pt["away"]
        _require(abs(s - 1.0) < 0.05, f"winprob[{i}] does not sum to 1 (got {s:.3f})")

    an = m["analytics"]
    _require(an["possession"][0] + an["possession"][1] == 100, "possession must sum to 100")
    return m
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_schema.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tiktok/matchsim/schema.py tiktok/matchsim/tests/test_schema.py
git commit -m "feat(matchsim): match-JSON schema validation"
```

---

### Task 8: `simulate` CLI

**Files:**
- Create: `tiktok/matchsim/cli.py`
- Test: `tiktok/matchsim/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

Create `tiktok/matchsim/tests/test_cli.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

CLI = str(Path(__file__).resolve().parents[1] / "cli.py")


def test_cli_writes_valid_json(tmp_path):
    out = tmp_path / "match.json"
    r = subprocess.run(
        [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
         "--competition", "ucl", "--seed", "21", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["fixture"]["home"]["abbr"] == "MUN"
    assert data["fixture"]["seed"] == 21
    assert data["events"][-1]["type"] == "full_time"


def test_cli_deterministic_stdout():
    base = [sys.executable, CLI, "simulate", "--home", "MUN", "--away", "RMA",
            "--seed", "21"]
    a = subprocess.run(base, capture_output=True, text=True)
    b = subprocess.run(base, capture_output=True, text=True)
    assert a.returncode == 0 and b.returncode == 0
    assert a.stdout == b.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tiktok/matchsim/tests/test_cli.py -v`
Expected: FAIL — the CLI file does not exist yet (non-zero return code / assertion error).

- [ ] **Step 3: Write the implementation**

Create `tiktok/matchsim/cli.py`:

```python
#!/usr/bin/env python3
"""MatchSim CLI. v1 (this plan) exposes `simulate` -> match JSON.

Usage:
    python tiktok/matchsim/cli.py simulate --home MUN --away RMA \
        --competition ucl --seed 21 [--home-xg 1.9 --away-xg 1.2] \
        [--venue "Old Trafford"] [--stage "Quarter-final"] [--date 2026-09-15] \
        [--out match.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine
import schema


def _cmd_simulate(args):
    m = engine.simulate(
        args.home, args.away, competition=args.competition, seed=args.seed,
        home_xg=args.home_xg, away_xg=args.away_xg,
        venue=args.venue, stage=args.stage, date=args.date,
    )
    schema.validate(m)
    # strip internal keys (prefixed with "_") from the emitted JSON
    public = {k: v for k, v in m.items() if not k.startswith("_")}
    text = json.dumps(public, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="MatchSim")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("simulate", help="simulate a match -> JSON")
    s.add_argument("--home", required=True)
    s.add_argument("--away", required=True)
    s.add_argument("--competition", default="generic")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--home-xg", type=float, default=None, dest="home_xg")
    s.add_argument("--away-xg", type=float, default=None, dest="away_xg")
    s.add_argument("--venue", default="")
    s.add_argument("--stage", default=None)
    s.add_argument("--date", default="")
    s.add_argument("--out", default=None)
    s.set_defaults(func=_cmd_simulate)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
```

Note: `schema.validate` runs on the full dict (including `_`-prefixed keys) before they are stripped for output — validation only checks the public keys, so this is fine.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tiktok/matchsim/tests/test_cli.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest tiktok/matchsim/tests/ -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 6: Manual smoke check**

Run: `python tiktok/matchsim/cli.py simulate --home MUN --away RMA --competition ucl --seed 21`
Expected: pretty-printed JSON with `fixture`, `events`, `winprob`, `analytics`; final event is `full_time`; no `_`-prefixed keys.

- [ ] **Step 7: Commit**

```bash
git add tiktok/matchsim/cli.py tiktok/matchsim/tests/test_cli.py
git commit -m "feat(matchsim): simulate CLI emitting match JSON"
```

---

## Self-Review

**Spec coverage (M1 scope):**
- Dixon-Coles reuse (vendored) → Task 1 ✓
- Live win-probability → Task 2 + Task 6 (track) ✓
- Team/competition presets + xG derivation + United emphasis data → Task 3 ✓ (United-red *rendering* treatment is Plan 2/3)
- Deterministic seeded simulation → Task 4 ✓
- Event timeline incl. near-miss flavours for captions → Task 5 ✓
- Win-prob track + credible analytics (possession/shots/xG) → Task 6 ✓
- Schema validation (inspectable JSON, NFR4) → Task 7 ✓
- CLI (`simulate`) → Task 8 ✓
- Out of Plan-1 scope (documented as later plans): `arena.py`, `captions.py`, `themes.py`, `render_match.py`, batch, SFX, three-act rendering. These are Plan 2 / Plan 3.

**Placeholder scan:** none — every step has full code and exact commands.

**Type/name consistency:** `resolve_team`/`resolve_competition`/`compute_xg` (presets) used consistently in engine; `simulate(home, away, competition, seed, home_xg, away_xg, venue, stage, date)` signature identical across Tasks 4/5/6/8; `_sample_score`, `_build_events`, `_winprob_track`, `_analytics`, `_disc` names stable; `win_prob(score_h, score_a, minutes_left, lam_h, lam_a, rho, max_goals)` used the same in Task 2 and Task 6; event types in `schema.EVENT_TYPES` match those produced by `_build_events` (`goal`, `near_miss`, `half_time`, `full_time`) plus reserved-for-Plan-2 (`clash`, `mystery_ball`).

**Note on internal keys:** `_final`/`_lam`/`_score` are internal conveniences used by tests and later plans; the CLI strips `_`-prefixed keys from emitted JSON so the public contract matches the spec's data model.
```
