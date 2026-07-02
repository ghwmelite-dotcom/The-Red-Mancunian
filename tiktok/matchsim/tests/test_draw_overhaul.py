import draw


def test_flag_disc_shape_and_clip():
    f = draw.flag_disc(120, ["#0055A4", "#FFFFFF", "#EF4135"], "v")
    assert f.size == (120, 120) and f.mode == "RGBA"
    assert f.getpixel((60, 60))[3] == 255      # centre opaque
    assert f.getpixel((2, 2))[3] == 0          # corner transparent (clipped)


def test_team_disc_dispatch():
    nation = {"flag": (["#FF0000", "#FFFFFF"], "h"), "color": "#FF0000", "monogram": "XXX"}
    club = {"flag": None, "color": "#DA020E", "monogram": "MUN"}
    assert draw.team_disc(100, nation).size == (100, 100)
    assert draw.team_disc(100, club).size == (100, 100)


def test_full_canvas_layers_sized():
    assert draw.pitch_texture(1080, 1920).size == (1080, 1920)
    assert draw.watermark(1080, 1920, "26", 540, 1000, 400).size == (1080, 1920)
    assert draw.crowd_ring(1080, 1920, 540, 1000, 430, 7, "#35e6c8").size == (1080, 1920)


def test_crowd_ring_deterministic():
    a = draw.crowd_ring(1080, 1920, 540, 1000, 430, 7, "#35e6c8")
    b = draw.crowd_ring(1080, 1920, 540, 1000, 430, 7, "#35e6c8")
    assert a.tobytes() == b.tobytes()


def test_small_pieces():
    assert draw.goal_net().mode == "RGBA"
    assert draw.caption_pill("CLASH!", "#F5C451").mode == "RGBA"
    assert draw.bottom_banner(1080, "WORLD CUP 26").size[0] == 1080
    t0 = draw.side_ticker(1920, "MATCHSIM", offset=0)
    t50 = draw.side_ticker(1920, "MATCHSIM", offset=50)
    assert t0.size == (60, 1920)
    assert t0.tobytes() != t50.tobytes()  # offset scrolls it
