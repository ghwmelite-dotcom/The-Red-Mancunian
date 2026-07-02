from engine import simulate
from prepare import prepare
from timeline import build_timeline, FPS


def _bundle(seed=21, frames=120):
    m = simulate("MUN", "RMA", competition="ucl", seed=seed)
    return prepare(m, n_frames=frames)


def test_total_and_acts():
    tl = build_timeline(_bundle(), fps=30, pre=2.0, live=4.0, post=2.0)
    assert tl["fps"] == 30
    assert tl["total"] == 60 + 120 + 60
    assert len(tl["frames"]) == tl["total"]
    pre, live, post = tl["acts"]["pre"], tl["acts"]["live"], tl["acts"]["post"]
    assert pre == (0, 60)
    assert live == (60, 180)
    assert post == (180, 240)


def test_frames_carry_their_act():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    acts = [f["act"] for f in tl["frames"]]
    assert acts[0] == "pre"
    assert acts[tl["acts"]["live"][0]] == "live"
    assert acts[-1] == "post"


def test_live_minute_runs_zero_to_ninety_monotonic():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    minutes = [f["minute"] for f in live]
    assert minutes[0] == 0.0
    assert abs(minutes[-1] - 90.0) < 1e-6
    assert minutes == sorted(minutes)


def test_live_clock_format():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    assert live[0]["clock"] == "00:00"
    for f in live:
        mm, ss = f["clock"].split(":")
        assert len(mm) == 2 and len(ss) == 2


def test_score_is_monotonic_and_matches_final_at_end():
    b = _bundle()
    tl = build_timeline(b, pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    h = [f["score"][0] for f in live]
    a = [f["score"][1] for f in live]
    assert h == sorted(h) and a == sorted(a)
    final = b["match"]["fixture"]["final"]
    assert f"{live[-1]['score'][0]}-{live[-1]['score'][1]}" == final


def test_each_goal_has_exactly_one_goal_frame():
    b = _bundle()
    tl = build_timeline(b, pre=2.0, live=8.0, post=2.0)
    goal_events = [e for e in b["match"]["events"] if e["type"] == "goal"]
    goal_frames = [f for f in tl["frames"] if f.get("goal")]
    assert len(goal_frames) == len(goal_events)


def test_winprob_interpolated_and_normalized():
    tl = build_timeline(_bundle(), pre=2.0, live=4.0, post=2.0)
    live = [f for f in tl["frames"] if f["act"] == "live"]
    for f in live:
        wp = f["winprob"]
        assert abs(wp["home"] + wp["draw"] + wp["away"] - 1.0) < 0.03


def test_motion_index_in_range():
    b = _bundle(frames=120)
    tl = build_timeline(b, pre=2.0, live=4.0, post=2.0)
    n = len(b["motion"])
    for f in tl["frames"]:
        if f["act"] == "live":
            assert 0 <= f["motion_index"] < n


def test_two_goals_same_minute_get_distinct_frames():
    bundle = {
        "match": {
            "events": [
                {"minute": 45, "type": "goal", "team": "home", "scorer": "A",
                 "scoreAfter": "1-0"},
                {"minute": 45, "type": "goal", "team": "away", "scorer": "B",
                 "scoreAfter": "1-1"},
                {"minute": 90, "type": "full_time", "scoreAfter": "1-1"},
            ],
            "winprob": [
                {"minute": 0, "home": 0.5, "draw": 0.3, "away": 0.2},
                {"minute": 90, "home": 0.3, "draw": 0.4, "away": 0.3},
            ],
            "fixture": {"final": "1-1"},
        },
        "motion": [{"home": [0, 0], "away": [0, 0], "ball": [0, 0], "clash": False}] * 50,
    }
    tl = build_timeline(bundle, pre=1.0, live=4.0, post=1.0)
    goal_frames = [f for f in tl["frames"] if f.get("goal")]
    assert len(goal_frames) == 2
    # the two goal frames are distinct frames
    idxs = [i for i, f in enumerate(tl["frames"]) if f.get("goal")]
    assert len(set(idxs)) == 2
    # both goal events are represented (distinct scorers)
    scorers = {f["goal"]["scorer"] for f in goal_frames}
    assert scorers == {"A", "B"}
