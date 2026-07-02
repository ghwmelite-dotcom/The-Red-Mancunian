"""Vendored Dixon-Coles bivariate-Poisson core.

Refactored out of the match-analyst skill's match_model.py so MatchSim is
self-contained (the skill's copy lives in a transient extracted dir).
Produces P(home i, away j) as a normalized score matrix.
"""
from math import exp, factorial


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * exp(-lam) / factorial(k)


def dc_tau(i, j, lam, mu, rho):
    """Dixon-Coles low-score dependency adjustment."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(home_xg, away_xg, rho=-0.05, max_goals=10):
    """Return matrix[i][j] = P(home scores i, away scores j), normalized."""
    m = [[0.0] * (max_goals + 1) for _ in range(max_goals + 1)]
    total = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = (poisson_pmf(i, home_xg)
                 * poisson_pmf(j, away_xg)
                 * dc_tau(i, j, home_xg, away_xg, rho))
            p = max(p, 0.0)  # tau can go slightly negative for extreme rho
            m[i][j] = p
            total += p
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i][j] /= total
    return m


def derive_markets(m):
    home = draw = away = 0.0
    for i in range(len(m)):
        for j in range(len(m)):
            p = m[i][j]
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    return {"1x2": {"home": home, "draw": draw, "away": away}}
