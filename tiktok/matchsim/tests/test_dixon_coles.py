from dixon_coles import poisson_pmf, score_matrix, derive_markets, dc_tau


def test_poisson_pmf_zero_lambda():
    assert poisson_pmf(0, 0.0) == 1.0
    assert poisson_pmf(1, 0.0) == 0.0


def test_score_matrix_sums_to_one():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    total = sum(m[i][j] for i in range(11) for j in range(11))
    assert abs(total - 1.0) < 1e-9


def test_derive_markets_probabilities_consistent():
    m = score_matrix(1.6, 1.1, rho=-0.05, max_goals=10)
    mk = derive_markets(m)
    o = mk["1x2"]
    assert abs(o["home"] + o["draw"] + o["away"] - 1.0) < 1e-9
    assert o["home"] > o["away"]


def test_dc_tau_low_score_adjustments():
    lam, mu, rho = 1.6, 1.1, -0.05
    assert dc_tau(0, 0, lam, mu, rho) == 1.0 - lam * mu * rho
    assert dc_tau(0, 1, lam, mu, rho) == 1.0 + lam * rho
    assert dc_tau(1, 0, lam, mu, rho) == 1.0 + mu * rho
    assert dc_tau(1, 1, lam, mu, rho) == 1.0 - rho
    assert dc_tau(2, 3, lam, mu, rho) == 1.0
