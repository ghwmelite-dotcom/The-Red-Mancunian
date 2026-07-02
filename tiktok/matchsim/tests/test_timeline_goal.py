from timeline import build_timeline


def _bundle():
    return {
        "match": {
            "events": [
                {"minute": 30, "type": "goal", "team": "home", "scorer": "A",
                 "scoreAfter": "1-0"},
                {"minute": 90, "type": "full_time", "scoreAfter": "1-0"},
            ],
            "winprob": [
                {"minute": 0, "home": 0.5, "draw": 0.3, "away": 0.2},
                {"minute": 30, "home": 0.7, "draw": 0.2, "away": 0.1},
                {"minute": 90, "home": 1.0, "draw": 0.0, "away": 0.0},
            ],
            "fixture": {"final": "1-0"},
        },
        "motion": [{"home": [0, 0], "away": [0, 0], "ball": [0, 0], "clash": False}] * 120,
    }


def _live(tl):
    return [f for f in tl["frames"] if f["act"] == "live"]


def test_all_live_frames_have_moving_net_angle():
    live = _live(build_timeline(_bundle(), pre=1.0, live=4.0, post=1.0))
    assert all(isinstance(f["net_angle"], float) for f in live)
    assert live[0]["net_angle"] != live[-1]["net_angle"]  # the goal moves


def test_goal_frame_scored_and_shot_completes():
    live = _live(build_timeline(_bundle(), pre=1.0, live=8.0, post=1.0))
    scored = [f for f in live if f["scored"]]
    assert len(scored) == 1
    assert scored[0]["shot_progress"] == 1.0
    assert scored[0]["shot_target"] is not None
    shot_frames = [f for f in live if f["shot_progress"] is not None]
    assert len(shot_frames) > 1
    assert any(f["shot_progress"] < 1.0 for f in shot_frames)  # ball flies in


def test_celebration_window_after_goal():
    live = _live(build_timeline(_bundle(), pre=1.0, live=8.0, post=1.0))
    celeb = [f for f in live if f["celebrate"] is not None]
    assert celeb
    assert [f for f in live if f["scored"]][0]["celebrate"] == 0.0
