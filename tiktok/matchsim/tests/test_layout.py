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
    for (x, y, w, h) in bands:
        assert 0 <= x and 0 <= y
        assert x + w <= W and y + h <= H
    order = [z["header"], z["scoreboard"], z["progress"], z["winprob"]]
    tops = [b[1] for b in order]
    assert tops == sorted(tops)
    for a, b in zip(order, order[1:]):
        assert a[1] + a[3] <= b[1] + 1


def test_arena_circle_inside_canvas():
    z = live_zones()
    cx, cy, r = z["arena"]
    assert r > 0
    assert cx - r >= 0 and cx + r <= W
    assert cy - r >= 0 and cy + r <= H
