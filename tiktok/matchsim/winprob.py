"""Live win probability: Dixon-Coles over the REMAINING match, folded onto
the current score. At minutes_left=0 the outcome is fully decided by the
current score.
"""
from dixon_coles import score_matrix


def win_prob(score_h, score_a, minutes_left, lam_h, lam_a, rho=-0.05, max_goals=8):
    frac = max(0.0, minutes_left / 90.0)
    m = score_matrix(lam_h * frac, lam_a * frac, rho, max_goals)
    home = draw = away = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            fh, fa = score_h + i, score_a + j
            p = m[i][j]
            if fh > fa:
                home += p
            elif fh == fa:
                draw += p
            else:
                away += p
    return {"home": home, "draw": draw, "away": away}
