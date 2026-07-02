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
    """Clamp an object inside the circle; reflect velocity only if it is
    moving outward (prevents a spurious kick when a push has displaced it)."""
    d = math.hypot(pos[0], pos[1])
    limit = R - obj_r
    if d > limit and d > 0:
        nx, ny = pos[0] / d, pos[1] / d
        pos[0], pos[1] = nx * limit, ny * limit
        dot = vel[0] * nx + vel[1] * ny
        if dot > 0:
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
    s = int(match["fixture"]["seed"] if seed is None else seed)
    rng = random.Random(s * 7919 + 13)  # decorrelate from the engine's rng

    home = {"pos": _rand_pos(rng), "vel": _rand_vel(rng)}
    away = {"pos": _rand_pos(rng), "vel": _rand_vel(rng)}
    ball = {"pos": [0.0, 0.0], "vel": _rand_vel(rng)}

    # Ensure discs don't start overlapping (capped retries, then force-place).
    for _ in range(64):
        if math.hypot(away["pos"][0] - home["pos"][0],
                      away["pos"][1] - home["pos"][1]) >= 2 * DISC_R:
            break
        away["pos"] = _rand_pos(rng)
    else:
        away["pos"] = [-home["pos"][0], -home["pos"][1]]  # opposite side

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
            push = overlap / 2 + 5e-4
            home["pos"][0] -= nx * push
            home["pos"][1] -= ny * push
            away["pos"][0] += nx * push
            away["pos"][1] += ny * push
            hv = home["vel"][0] * nx + home["vel"][1] * ny
            av = away["vel"][0] * nx + away["vel"][1] * ny
            home["vel"][0] += (av - hv) * nx
            home["vel"][1] += (av - hv) * ny
            away["vel"][0] += (hv - av) * nx
            away["vel"][1] += (hv - av) * ny

        _reflect_inside(home["pos"], home["vel"], DISC_R)
        _reflect_inside(away["pos"], away["vel"], DISC_R)

        frames.append({
            "home": [round(home["pos"][0], 4), round(home["pos"][1], 4)],
            "away": [round(away["pos"][0], 4), round(away["pos"][1], 4)],
            "ball": [round(ball["pos"][0], 4), round(ball["pos"][1], 4)],
            "clash": clash,
        })
    return frames
