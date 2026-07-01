from engine import simulate
from prepare import prepare


def test_bundle_shape():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    b = prepare(m, n_frames=100)
    assert set(b) == {"match", "theme", "motion"}
    assert b["match"] is m
    assert b["theme"]["key"] == "ucl"
    assert len(b["motion"]) == 100


def test_united_match_gets_red_treatment():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    b = prepare(m, n_frames=10)
    assert b["theme"]["united_home"] is True
    assert b["theme"]["accent"] == "#DA020E"


def test_non_united_match_keeps_theme_accent():
    m = simulate("LIV", "ARS", competition="epl", seed=5)
    b = prepare(m, n_frames=10)
    assert b["theme"]["united_home"] is False
    assert b["theme"]["accent"] != "#DA020E"


def test_motion_seeded_from_match():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    a = prepare(m, n_frames=50)["motion"]
    b = prepare(m, n_frames=50)["motion"]
    assert a == b
