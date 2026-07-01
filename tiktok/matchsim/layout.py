"""Zone geometry for the live-sim frame (1080x1920). Pure — returns rectangles
and the arena circle so drawing code never hard-codes coordinates.

Rect convention: (x, y, w, h). Arena: (cx, cy, r).
"""
W, H = 1080, 1920
MARGIN = 64


def live_zones():
    header = (MARGIN, 96, W - 2 * MARGIN, 70)
    scoreboard = (MARGIN, 186, W - 2 * MARGIN, 130)
    progress = (MARGIN, 336, W - 2 * MARGIN, 14)
    winprob = (MARGIN, 376, W - 2 * MARGIN, 96)

    arena_top = 540
    arena_bottom = H - 250
    r = min((W - 2 * MARGIN) // 2, (arena_bottom - arena_top) // 2)
    cx = W // 2
    cy = arena_top + r

    score_anchors = (W // 2 - 210, W // 2, W // 2 + 210)
    caption = (MARGIN, H - 210, W - 2 * MARGIN, 90)
    return {
        "header": header, "scoreboard": scoreboard, "progress": progress,
        "winprob": winprob, "arena": (cx, cy, r), "caption": caption,
        "score_anchors": score_anchors,
    }
