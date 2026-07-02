"""Align the match (minutes) to video frames (30fps) across three acts.

Emits a per-frame render schedule so goals, the accelerated clock, the score,
and the win-prob swing land on exact frames — the piece the renderer needs that
the raw bundle doesn't carry.
"""
import math

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

    # Assign each goal to the nearest UNCLAIMED live frame, so two goals in the
    # same minute take adjacent frames instead of one overwriting the other.
    live_frames = frames[live_start:live_start + live_n]
    claimed = set()
    for g in sorted(goals, key=lambda e: e["minute"]):
        order = sorted(range(len(live_frames)),
                       key=lambda k: (abs(live_frames[k]["minute"] - g["minute"]), k))
        for k in order:
            if k not in claimed:
                live_frames[k]["goal"] = g
                claimed.add(k)
                break

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

    # --- Moving goal + ball-into-net scripting (the goal "wow" moment) ---
    # Goal net sweeps ~270deg around the ring across the match; at each goal the
    # ball flies into the net (shot_progress 0->1), crosses the line (scored),
    # then a short celebration window animates the GOAL burst.
    SHOT = 16
    CELEB = 20
    goal_idx = [i for i, f in enumerate(live_frames) if f.get("goal")]

    def _net_angle(i):
        return math.pi / 2 + (i / max(live_n - 1, 1)) * 2 * math.pi * 0.75

    for i, f in enumerate(live_frames):
        f["net_angle"] = _net_angle(i)
        f["scored"] = False
        f["shot_progress"] = None
        f["shot_target"] = None
        f["celebrate"] = None

    for gi in goal_idx:
        a = _net_angle(gi)
        tgt = [math.cos(a) * 0.9, math.sin(a) * 0.9]  # ball target = net mouth
        live_frames[gi]["scored"] = True
        start = max(0, gi - SHOT)
        span = gi - start
        for i in range(start, gi + 1):
            live_frames[i]["shot_progress"] = (i - start) / span if span else 1.0
            live_frames[i]["shot_target"] = tgt
        for i in range(gi, min(live_n, gi + CELEB + 1)):
            live_frames[i]["celebrate"] = (i - gi) / CELEB
            live_frames[i]["shot_target"] = tgt  # ball stays in the net during celebration

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
