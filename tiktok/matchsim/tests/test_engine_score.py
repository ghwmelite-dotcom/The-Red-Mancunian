from engine import simulate


def test_deterministic_same_seed():
    a = simulate("MUN", "RMA", competition="ucl", seed=42)
    b = simulate("MUN", "RMA", competition="ucl", seed=42)
    assert a == b


def test_different_seed_can_differ():
    a = simulate("MUN", "RMA", competition="ucl", seed=1)
    b = simulate("MUN", "RMA", competition="ucl", seed=2)
    assert a["fixture"]["seed"] == 1
    assert b["fixture"]["seed"] == 2


def test_fixture_block_shape():
    m = simulate("MUN", "RMA", competition="ucl", seed=7, venue="Old Trafford")
    fx = m["fixture"]
    assert fx["home"]["abbr"] == "MUN"
    assert fx["away"]["abbr"] == "RMA"
    assert fx["competition"] == "ucl"
    assert fx["venue"] == "Old Trafford"
    assert fx["final"] == m["_final"]


def test_xg_override_used():
    m = simulate("MUN", "RMA", seed=3, home_xg=3.0, away_xg=0.1)
    sh, sa = (int(x) for x in m["_final"].split("-"))
    assert sh >= sa
