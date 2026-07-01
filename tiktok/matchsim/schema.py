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
