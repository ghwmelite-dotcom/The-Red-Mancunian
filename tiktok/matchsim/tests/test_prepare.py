from engine import simulate
from prepare import prepare


def test_bundle_shape():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    b = prepare(m, n_frames=100)
    assert set(b) == {"match", "theme", "motion"}
    assert b["match"] is m
    assert b["theme"]["key"] == "ucl"
    assert len(b["motion"]) == 100


def test_brand_first_every_match_wears_the_brand():
    # brand-first: the RED MANCUNIAN palette is on every video; the competition
    # only supplies the neon ring tint (theme.accent), never the base palette.
    for home, away, comp, ring in [("MUN", "RMA", "ucl", "#39E6E6"),
                                    ("LIV", "ARS", "epl", "#00FF87")]:
        b = prepare(simulate(home, away, competition=comp, seed=5), n_frames=10)
        t = b["theme"]
        assert t["bg"] == ["#1C1310", "#2A0F0E", "#781414"]  # brand ink->dark-red
        assert t["red"] == "#C6241E" and t["gold"] == "#F5C451"
        assert t["accent"] == ring  # competition ring tint only


def test_united_flag_still_tracked():
    assert prepare(simulate("MUN", "RMA", competition="ucl", seed=21),
                   n_frames=10)["theme"]["united_home"] is True
    assert prepare(simulate("LIV", "ARS", competition="epl", seed=5),
                   n_frames=10)["theme"]["united_home"] is False


def test_motion_seeded_from_match():
    m = simulate("MUN", "RMA", competition="ucl", seed=21)
    a = prepare(m, n_frames=50)["motion"]
    b = prepare(m, n_frames=50)["motion"]
    assert a == b
