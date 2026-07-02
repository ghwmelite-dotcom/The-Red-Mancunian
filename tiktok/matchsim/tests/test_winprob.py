from winprob import win_prob


def test_sums_to_one_at_kickoff():
    wp = win_prob(0, 0, minutes_left=90, lam_h=1.6, lam_a=1.1)
    assert abs(wp["home"] + wp["draw"] + wp["away"] - 1.0) < 1e-9


def test_full_time_decided_by_current_score():
    wp = win_prob(2, 1, minutes_left=0, lam_h=1.6, lam_a=1.1)
    assert wp["home"] == 1.0
    assert wp["draw"] == 0.0
    assert wp["away"] == 0.0


def test_full_time_draw():
    wp = win_prob(1, 1, minutes_left=0, lam_h=1.6, lam_a=1.1)
    assert wp["draw"] == 1.0


def test_a_home_goal_raises_home_probability():
    before = win_prob(0, 0, minutes_left=60, lam_h=1.4, lam_a=1.4)
    after = win_prob(1, 0, minutes_left=60, lam_h=1.4, lam_a=1.4)
    assert after["home"] > before["home"]
