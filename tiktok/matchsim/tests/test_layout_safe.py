from layout import live_zones, W


def test_header_below_tiktok_top_ui():
    z = live_zones()
    _, hy, _, _ = z["header"]
    assert hy >= 80


def test_score_anchors_symmetric_about_centre():
    z = live_zones()
    home_x, score_x, away_x = z["score_anchors"]
    assert score_x == W // 2
    assert W // 2 - home_x == away_x - W // 2
    assert home_x < score_x < away_x
