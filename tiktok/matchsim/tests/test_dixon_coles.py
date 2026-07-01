from dixon_coles import poisson_pmf, score_matrix, derive_markets


def test_poisson_pmf_zero_lambda():
    assert poisson_pmf(0, 0.0) == 1.0
    assert poisson_pmf(1, 0.0) == 0.0


def test_score_matrix_sums_to_one():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    total = sum(m[i][j] for i in range(11) for j in range(11))
    assert abs(total - 1.0) < 1e-9


def test_derive_markets_probabilities_consistent():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    mk = derive_markets(m, 10)
    o = mk["1x2"]
    assert abs(o["home"] + o["draw"] + o["away"] - 1.0) < 1e-9
    assert o["home"] > o["away"]
