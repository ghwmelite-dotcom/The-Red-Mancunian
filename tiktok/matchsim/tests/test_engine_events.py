from engine import simulate
from presets import resolve_team


def _events(m):
    return m["events"]


def test_goal_count_matches_final_score():
    m = simulate("MUN", "RMA", seed=11)
    sh, sa = (int(x) for x in m["fixture"]["final"].split("-"))
    goals = [e for e in _events(m) if e["type"] == "goal"]
    assert len([g for g in goals if g["team"] == "home"]) == sh
    assert len([g for g in goals if g["team"] == "away"]) == sa


def test_has_half_time_and_full_time():
    ev = _events(simulate("MUN", "RMA", seed=11))
    types = [e["type"] for e in ev]
    assert types.count("half_time") == 1
    assert types.count("full_time") == 1
    assert ev[-1]["type"] == "full_time"


def test_events_sorted_by_minute():
    ev = _events(simulate("MUN", "RMA", seed=11))
    minutes = [e["minute"] for e in ev]
    assert minutes == sorted(minutes)


def test_full_time_scoreafter_matches_final():
    m = simulate("MUN", "RMA", seed=11)
    ft = [e for e in _events(m) if e["type"] == "full_time"][0]
    assert ft["scoreAfter"] == m["fixture"]["final"]


def test_goals_have_scorer_from_pool():
    m = simulate("MUN", "RMA", seed=5, home_xg=3.0, away_xg=0.05)
    pool = set(resolve_team("MUN")["scorers"])
    home_goals = [e for e in _events(m) if e["type"] == "goal" and e["team"] == "home"]
    assert home_goals  # near-certain with xG 3.0
    assert all(g["scorer"] in pool for g in home_goals)


def test_half_time_scoreafter_reflects_first_half_goals():
    m = simulate("MUN", "RMA", seed=11)
    ev = _events(m)
    ht = next(e for e in ev if e["type"] == "half_time")
    ft = next(e for e in ev if e["type"] == "full_time")
    ht_h, ht_a = (int(x) for x in ht["scoreAfter"].split("-"))
    ft_h, ft_a = (int(x) for x in ft["scoreAfter"].split("-"))
    # half-time totals can't exceed full-time totals
    assert ht_h <= ft_h and ht_a <= ft_a
    # goals struck after minute 45 must account for the HT->FT difference
    second_half = [e for e in ev if e["type"] == "goal" and e["minute"] > 45]
    sh2 = sum(1 for g in second_half if g["team"] == "home")
    sa2 = sum(1 for g in second_half if g["team"] == "away")
    assert ht_h + sh2 == ft_h
    assert ht_a + sa2 == ft_a


def test_near_miss_events_present_with_flavour():
    ev = _events(simulate("MUN", "RMA", seed=11))
    nm = [e for e in ev if e["type"] == "near_miss"]
    assert nm
    assert all(e["flavour"] in {"woodwork", "big_chance", "clash"} for e in nm)
