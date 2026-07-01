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
