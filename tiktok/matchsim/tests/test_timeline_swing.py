from timeline import build_timeline


def _bundle_with_goal():
    return {
        "match": {
            "events": [
                {"minute": 30, "type": "goal", "team": "home", "scorer": "A",
                 "scoreAfter": "1-0"},
                {"minute": 90, "type": "full_time", "scoreAfter": "1-0"},
            ],
            "winprob": [
                {"minute": 0, "home": 0.50, "draw": 0.30, "away": 0.20},
                {"minute": 30, "home": 0.72, "draw": 0.18, "away": 0.10},
                {"minute": 90, "home": 1.0, "draw": 0.0, "away": 0.0},
            ],
            "fixture": {"final": "1-0"},
        },
        "motion": [{"home": [0, 0], "away": [0, 0], "ball": [0, 0], "clash": False}] * 60,
    }


def test_goal_frame_has_swing_with_team_and_delta():
    tl = build_timeline(_bundle_with_goal(), pre=1.0, live=4.0, post=1.0)
    goal_frames = [f for f in tl["frames"] if f.get("goal")]
    assert len(goal_frames) == 1
    sw = goal_frames[0]["swing"]
    assert sw["team"] == "home"
    assert sw["delta"] == 22


def test_non_goal_live_frames_have_no_swing():
    tl = build_timeline(_bundle_with_goal(), pre=1.0, live=4.0, post=1.0)
    non_goal_live = [f for f in tl["frames"]
                     if f["act"] == "live" and not f.get("goal")]
    assert all("swing" not in f for f in non_goal_live)
