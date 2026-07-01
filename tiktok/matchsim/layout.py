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
