from engine import simulate


def test_winprob_track_present_and_normalized():
    m = simulate("MUN", "RMA", seed=9)
    track = m["winprob"]
    assert track and track[0]["minute"] == 0
    assert track[-1]["minute"] == 90
    for pt in track:
        assert abs(pt["home"] + pt["draw"] + pt["away"] - 1.0) < 0.02


def test_winprob_track_includes_every_goal_minute():
    m = simulate("MUN", "RMA", seed=9)
    goal_minutes = {e["minute"] for e in m["events"] if e["type"] == "goal"}
    track_minutes = {pt["minute"] for pt in m["winprob"]}
    assert goal_minutes <= track_minutes


def test_analytics_shape():
    m = simulate("MUN", "RMA", seed=9)
    an = m["analytics"]
    assert an["possession"][0] + an["possession"][1] == 100
    sh, sa = m["_score"]
    assert an["shots"][0] >= sh and an["shots"][1] >= sa
    assert an["xg"][0] > 0 and an["xg"][1] > 0
