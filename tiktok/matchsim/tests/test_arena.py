import math
from arena import simulate_motion, R, DISC_R


def _match(seed=21):
    return {"fixture": {"seed": seed}}


def test_frame_count_matches_request():
    frames = simulate_motion(_match(), n_frames=120)
    assert len(frames) == 120


def test_frame_shape():
    f = simulate_motion(_match(), n_frames=1)[0]
    assert set(f) == {"home", "away", "ball", "clash"}
    assert len(f["home"]) == 2 and len(f["ball"]) == 2
    assert isinstance(f["clash"], bool)


def test_discs_and_ball_stay_inside_arena():
    frames = simulate_motion(_match(), n_frames=400)
    for f in frames:
        assert math.hypot(*f["home"]) <= R + 1e-6
        assert math.hypot(*f["away"]) <= R + 1e-6
        assert math.hypot(*f["ball"]) <= R + 1e-6


def test_discs_never_overlap_after_a_frame_is_recorded():
    frames = simulate_motion(_match(), n_frames=400)
    for f in frames:
        dist = math.hypot(f["away"][0] - f["home"][0], f["away"][1] - f["home"][1])
        assert dist >= 2 * DISC_R - 1e-6


def test_deterministic_same_seed():
    a = simulate_motion(_match(21), n_frames=200)
    b = simulate_motion(_match(21), n_frames=200)
    assert a == b


def test_different_seed_diverges():
    a = simulate_motion(_match(1), n_frames=200)
    b = simulate_motion(_match(2), n_frames=200)
    assert a != b


def test_explicit_seed_overrides_fixture_seed():
    a = simulate_motion(_match(1), n_frames=50, seed=999)
    b = simulate_motion(_match(2), n_frames=50, seed=999)
    assert a == b


def test_some_clash_occurs_over_a_long_run():
    frames = simulate_motion(_match(), n_frames=1200)
    assert any(f["clash"] for f in frames)
